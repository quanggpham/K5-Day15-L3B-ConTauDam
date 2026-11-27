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
            ('L1', 'K', 1, True, 'c'), ('L1', 'K', 1, False, 'd'), ('L1', 'K', 1, True, 'e'),
            ('L1', 'K', 1, None, 'f'), ('L1', 'K', 2, False, 'g')]
    snap = build_snapshot(make_db(rows))
    k = kc(snap, 'L1', 'K')
    assert (k['graded_count'], k['learner_count'], k['ungraded_count']) == (6, 5, 1)
    assert snap['lessons']['L1']['sample'] == {'responses': 6, 'learners': 5, 'ungraded': 1, 'incorrect': 3,
                                               'masked_kc_count': 0}


def test_delta_vs_previous_lesson_in_percentage_points():
    rows = [('L1', 'K', 1, i >= 2, str(i)) for i in range(10)] + [('L2', 'K', 1, i >= 5, str(i)) for i in range(10)]
    snap = build_snapshot(make_db(rows))
    assert snap['lessons']['L1']['delta_vs_previous_pp'] is None
    assert snap['lessons']['L2']['previous_lesson_id'] == 'L1'
    assert snap['lessons']['L2']['delta_vs_previous_pp'] == 30.0
    assert kc(snap, 'L2', 'K')['delta_vs_previous_pp'] == 30.0


def graded_rows(lesson, code, wrong, total=10):
    return [(lesson, code, 1, i >= wrong, f'{lesson}{code}{i}') for i in range(total)]


def test_natural_sort_catalog_previous_and_latest():
    from codebase.backend.analytics.metrics import lesson_sort_key
    assert sorted(['L10', 'L2', 'L1'], key=lesson_sort_key) == ['L1', 'L2', 'L10']
    rows = graded_rows('L1', 'K', 1) + graded_rows('L10', 'K', 5) + graded_rows('L2', 'K', 3)
    snap = build_snapshot(make_db(rows))
    assert [c['lesson_id'] for c in snap['catalog']] == ['L1', 'L2', 'L10']
    assert snap['catalog'][-1]['lesson_id'] == 'L10'
    assert snap['lessons']['L10']['previous_lesson_id'] == 'L2'
    assert snap['lessons']['L2']['previous_lesson_id'] == 'L1'
    assert snap['lessons']['L10']['delta_vs_previous_pp'] == 20.0
    assert kc(snap, 'L10', 'K')['delta_vs_previous_pp'] == 20.0


def test_previous_lesson_no_graded_gives_none_delta_not_older_lesson():
    rows = graded_rows('L1', 'K', 2) + [('L2', 'K', 1, None, 'x'), ('L2', 'K', 1, None, 'y')] \
        + graded_rows('L3', 'K', 5)
    snap = build_snapshot(make_db(rows))
    l3 = snap['lessons']['L3']
    assert snap['lessons']['L2']['status'] == 'no_graded'
    assert l3['previous_lesson_id'] == 'L2' and l3['delta_vs_previous_pp'] is None
    assert kc(snap, 'L3', 'K')['delta_vs_previous_pp'] is None


def test_kc_absent_in_previous_lesson_gives_none_delta():
    rows = graded_rows('L1', 'A', 2) + graded_rows('L1', 'B', 4) + graded_rows('L2', 'B', 6) \
        + graded_rows('L3', 'A', 5) + graded_rows('L3', 'B', 7)
    snap = build_snapshot(make_db(rows))
    assert kc(snap, 'L3', 'A')['delta_vs_previous_pp'] is None  # A vắng ở L2, không so với L1
    assert kc(snap, 'L3', 'B')['delta_vs_previous_pp'] == 10.0
    assert kc(snap, 'L2', 'B')['delta_vs_previous_pp'] == 20.0
    assert snap['lessons']['L3']['delta_vs_previous_pp'] == 0.0  # L2 6/10 -> L3 12/20


def test_zero_incorrect_kc_not_in_priority_but_listed_ok():
    rows = graded_rows('L1', 'A', 3) + graded_rows('L1', 'Z', 0)
    snap = build_snapshot(make_db(rows))
    z = kc(snap, 'L1', 'Z')
    assert z['status'] == 'ok' and z['incorrect_rate'] == 0.0
    assert [p['kc_code'] for p in snap['lessons']['L1']['priority']] == ['A']


def test_v2_path_prefers_explicit_env(tmp_path, monkeypatch):
    import json
    from codebase.backend.analytics.snapshot import read_snapshot_v2
    explicit = tmp_path / 'elsewhere' / 'v2.json'
    explicit.parent.mkdir()
    explicit.write_text(json.dumps({'version': 2, 'catalog': [{'lesson_id': 'X'}], 'lessons': {}}), encoding='utf-8')
    (tmp_path / 'aggregate.v2.json').write_text(json.dumps({'version': 2, 'catalog': [], 'lessons': {}}),
                                                 encoding='utf-8')
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_PATH', str(tmp_path / 'aggregate.json'))
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(explicit))
    assert read_snapshot_v2()['catalog'] == [{'lesson_id': 'X'}]


def test_v2_path_derived_from_v1_dir_when_env_unset(tmp_path, monkeypatch):
    import json
    from codebase.backend.analytics.snapshot import read_snapshot_v2
    monkeypatch.delenv('AGGREGATE_SNAPSHOT_V2_PATH', raising=False)
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_PATH', str(tmp_path / 'aggregate.json'))
    assert read_snapshot_v2() is None  # chưa có file v2 cạnh v1
    (tmp_path / 'aggregate.v2.json').write_text(
        json.dumps({'version': 2, 'catalog': [{'lesson_id': 'Y'}], 'lessons': {}}), encoding='utf-8')
    assert read_snapshot_v2()['catalog'] == [{'lesson_id': 'Y'}]
