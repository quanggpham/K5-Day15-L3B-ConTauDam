import duckdb
from codebase.backend.analytics.metrics import build_snapshot


def make_db(rows):
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', rows)
    return db


def kc(snap, lesson, code):
    return next(k for k in snap['lessons'][lesson]['kcs'] if k['kc_code'] == code)


def test_version_catalog_and_no_learner_ids():
    snap = build_snapshot(make_db([('L1', 'K', 1, True, 'secret-a')]), generated_at='t')
    assert snap['version'] == 2 and snap['generated_at'] == 't'
    assert [c['lesson_id'] for c in snap['catalog']] == ['L1']
    assert 'secret-a' not in str(snap)


def test_zero_denominator_has_own_status_not_zero_percent():
    snap = build_snapshot(make_db([('L1', 'K', 1, None, 'a'), ('L1', 'K', 1, None, 'b')]))
    k = kc(snap, 'L1', 'K')
    assert k['status'] == 'no_graded' and k['incorrect_rate'] is None and k['ungraded_count'] == 2
    assert snap['lessons']['L1']['incorrect_rate'] is None and snap['lessons']['L1']['priority'] == []


def test_under_ten_flagged_kept_but_not_ranked():
    snap = build_snapshot(make_db([('L1', 'K', 1, False, str(i)) for i in range(9)]))
    k = kc(snap, 'L1', 'K')
    assert k['status'] == 'insufficient_sample' and k['incorrect_rate'] == 1.0
    assert snap['lessons']['L1']['priority'] == []


def test_ties_crossing_top3_return_whole_group():
    rows = []
    for code, wrong in [('A', 10), ('B', 5), ('C', 5), ('D', 5), ('E', 5), ('F', 0)]:
        rows += [('L1', code, 1, i >= wrong, f'{code}{i}') for i in range(10)]
    snap = build_snapshot(make_db(rows))
    pri = [(p['kc_code'], p['rank']) for p in snap['lessons']['L1']['priority']]
    assert pri == [('A', 1), ('B', 2), ('C', 2), ('D', 2), ('E', 2)]


def test_ungraded_and_retries_excluded_and_unique_learners():
    rows = [('L1', 'K', 1, False, 'a'), ('L1', 'K', 1, False, 'a'), ('L1', 'K', 1, True, 'b'),
            ('L1', 'K', 1, None, 'c'), ('L1', 'K', 2, False, 'd')]
    snap = build_snapshot(make_db(rows))
    k = kc(snap, 'L1', 'K')
    assert (k['graded_count'], k['learner_count'], k['ungraded_count']) == (3, 2, 1)
    assert snap['lessons']['L1']['sample'] == {'responses': 3, 'learners': 2, 'ungraded': 1, 'incorrect': 2}


def test_delta_vs_previous_lesson_in_percentage_points():
    rows = [('L1', 'K', 1, i >= 2, str(i)) for i in range(10)] + [('L2', 'K', 1, i >= 5, str(i)) for i in range(10)]
    snap = build_snapshot(make_db(rows))
    assert snap['lessons']['L1']['delta_vs_previous_pp'] is None
    assert snap['lessons']['L2']['previous_lesson_id'] == 'L1'
    assert snap['lessons']['L2']['delta_vs_previous_pp'] == 30.0
    assert kc(snap, 'L2', 'K')['delta_vs_previous_pp'] == 30.0
