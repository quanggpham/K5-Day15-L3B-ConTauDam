"""Ẩn số liệu KC có dưới 5 người: không lộ đúng/sai của từng học viên (k-anonymity, k=5)."""
import pytest

from codebase.backend.analytics.metrics import MIN_LEARNERS, build_snapshot
from tests.test_snapshot_v2 import kc, make_db


def _kc_rows(lesson, code, learners, per_learner, wrong_every=2):
    """`learners` người, mỗi người `per_learner` lượt đầu; một nửa số lượt sai."""
    return [(lesson, code, 1, (i % wrong_every) != 0, f'{code}-{n}')
            for n in range(learners) for i in range(per_learner)]


def test_threshold_is_five_unique_learners_not_responses():
    assert MIN_LEARNERS == 5
    snap = build_snapshot(make_db(_kc_rows('L1', 'FOUR', 4, 10) + _kc_rows('L1', 'FIVE', 5, 1)))
    four, five = kc(snap, 'L1', 'FOUR'), kc(snap, 'L1', 'FIVE')
    assert four['status'] == 'small_group'  # 40 lượt nhưng chỉ 4 người
    assert five['status'] == 'insufficient_sample' and five['graded_count'] == 5 and five['learner_count'] == 5


def test_masked_kc_exposes_no_numbers_and_is_never_ranked():
    snap = build_snapshot(make_db(_kc_rows('L1', 'S', 2, 20) + _kc_rows('L1', 'BIG', 12, 1)))
    masked = kc(snap, 'L1', 'S')
    assert masked['status'] == 'small_group'
    for field in ('graded_count', 'learner_count', 'incorrect_count', 'ungraded_count', 'incorrect_rate',
                  'delta_vs_previous_pp'):
        assert masked[field] is None
    assert 'S' not in {p['kc_code'] for p in snap['lessons']['L1']['priority']}


def test_lesson_totals_exclude_masked_kcs_so_subtraction_reveals_nothing():
    snap = build_snapshot(make_db(_kc_rows('L1', 'S', 3, 4) + _kc_rows('L1', 'BIG', 10, 2)))
    lesson = snap['lessons']['L1']
    visible = [k for k in lesson['kcs'] if k['status'] != 'small_group']
    assert lesson['sample']['masked_kc_count'] == 1
    assert lesson['sample']['responses'] == sum(k['graded_count'] for k in visible) == 20
    assert lesson['sample']['incorrect'] == sum(k['incorrect_count'] for k in visible)
    assert lesson['sample']['ungraded'] == sum(k['ungraded_count'] for k in visible)
    # tổng bài trừ KC hiển thị luôn bằng 0: không suy ra được phần đã ẩn
    assert lesson['sample']['responses'] - sum(k['graded_count'] for k in visible) == 0


def test_whole_lesson_with_few_learners_is_fully_masked():
    snap = build_snapshot(make_db(_kc_rows('L1', 'A', 3, 6) + _kc_rows('L1', 'B', 2, 6)))
    lesson = snap['lessons']['L1']
    assert lesson['status'] == 'small_group' and lesson['incorrect_rate'] is None
    assert lesson['sample']['responses'] is None and lesson['sample']['learners'] is None
    assert lesson['priority'] == []
    assert snap['catalog'][0]['sample']['responses'] is None and snap['catalog'][0]['status'] == 'small_group'


def test_delta_never_compares_against_a_masked_previous_value():
    rows = _kc_rows('L1', 'K', 3, 5) + _kc_rows('L2', 'K', 12, 1)
    snap = build_snapshot(make_db(rows + _kc_rows('L1', 'OTHER', 10, 1)))
    assert kc(snap, 'L2', 'K')['delta_vs_previous_pp'] is None  # KC ở bài trước bị ẩn nên không có giá trị để so
    assert snap['lessons']['L2']['previous_lesson_id'] == 'L1'


def test_no_graded_kc_stays_no_graded_not_masked():
    snap = build_snapshot(make_db([('L1', 'K', 1, None, 'a'), ('L1', 'K', 1, None, 'b')] + _kc_rows('L1', 'BIG', 10, 1)))
    assert kc(snap, 'L1', 'K')['status'] == 'no_graded' and kc(snap, 'L1', 'K')['ungraded_count'] == 2


@pytest.mark.parametrize('learners', [1, 2, 3, 4])
def test_every_count_below_threshold_is_masked(learners):
    snap = build_snapshot(make_db(_kc_rows('L1', 'S', learners, 12) + _kc_rows('L1', 'BIG', 8, 2)))
    assert kc(snap, 'L1', 'S')['status'] == 'small_group'


def test_lesson_is_masked_when_every_graded_kc_is_masked_even_if_union_of_learners_is_large():
    rows = _kc_rows('L1', 'A', 3, 4) + [('L1', 'B', 1, i % 2 == 0, f'B-{i % 3 + 10}') for i in range(12)]
    snap = build_snapshot(make_db(rows))  # 6 người khác nhau toàn bài, nhưng mỗi KC chỉ 3 người
    lesson = snap['lessons']['L1']
    assert all(k['status'] == 'small_group' for k in lesson['kcs'])
    assert lesson['status'] == 'small_group' and lesson['sample']['learners'] is None
