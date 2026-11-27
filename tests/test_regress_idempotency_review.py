"""Hồi quy idempotency tạo run và máy trạng thái duyệt (plan 001 step 10, mục b và d).

Spec: "Cùng mã và bài trả cùng bản nháp. Mã đã dùng cho bài khác trả xung đột"; "Phiên bản cũ nhận 409 và UI yêu cầu
tải lại trước khi lưu tiếp"; bản sửa tay "không thừa hưởng điểm JEV". Bảng chuyển trạng thái đối chiếu với văn bản SQL.
"""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codebase.backend.api.run_repository import REVIEW_TRANSITIONS
from codebase.backend.main import app
from tests.regression_support import (  # noqa: F401
    copilot, create_run, review, rg_coach, rg_repo, rg_snap, state_of)
from tests.test_analysis_runs import COACH_A, COACH_B

SQL = (Path(__file__).resolve().parents[1] / 'supabase/migrations/20261127000004_review_recommendation_rpc.sql'
       ).read_text(encoding='utf-8')
STATES = ('pending', 'accepted', 'rejected', 'changes_requested', 'edited')
DECISIONS = ('accept', 'reject', 'request_changes', 'edited')


# --- (b) idempotency tạo run ---

def _parallel_posts(repo, bodies, owner_switch):
    """Tất cả request cùng đi qua find_by_request (None) rồi mới chạm insert: dựng race thật, không sleep."""
    barrier = threading.Barrier(len(bodies), timeout=5)

    def gate(owner, row):
        try:
            barrier.wait()
        except threading.BrokenBarrierError:  # triển khai khoá sớm hơn cũng chấp nhận được
            pass
    repo.before_insert = gate

    def post(body):
        return TestClient(app).post('/api/analysis-runs', json=body)
    with ThreadPoolExecutor(len(bodies)) as pool:
        return list(pool.map(post, bodies))


def test_many_concurrent_creates_with_same_request_yield_one_run(rg_coach, rg_snap, rg_repo):
    rg_coach(COACH_A)
    body = {'lesson_id': 'L2', 'request_id': 'race-1'}
    results = _parallel_posts(rg_repo, [body] * 6, None)
    assert sorted(r.status_code for r in results) == [200] * 5 + [201]
    assert len({r.json()['run_id'] for r in results}) == 1 and len(rg_repo.runs) == 1
    assert sorted(r.json()['created'] for r in results) == [False] * 5 + [True]


def test_concurrent_same_request_with_different_lessons_gives_one_winner_and_409(rg_coach, rg_snap, rg_repo):
    rg_coach(COACH_A)
    results = _parallel_posts(rg_repo, [{'lesson_id': 'L1', 'request_id': 'race-2'},
                                        {'lesson_id': 'L2', 'request_id': 'race-2'}], None)
    assert sorted(r.status_code for r in results) == [201, 409]
    [run] = rg_repo.runs.values()
    winner = next(r for r in results if r.status_code == 201)
    assert winner.json()['run_id'] == run['id'] and winner.json()['lesson_id'] == run['lesson_id']


def test_retry_response_equals_first_response_except_created_flag(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    first = c.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'same'})
    retry = c.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'same'})
    assert (first.status_code, retry.status_code) == (201, 200)
    assert {**retry.json(), 'created': True} == first.json()  # cùng run, cùng thời điểm tạo, cùng phiên bản snapshot


def test_conflict_409_creates_nothing_and_leaves_first_run_untouched(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c, 'L1', 'dup')
    before = state_of(rg_repo)
    res = c.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'dup'})
    assert res.status_code == 409 and 'run_id' not in res.json()
    assert state_of(rg_repo) == before
    assert c.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'dup'}).json()['run_id'] == run_id


def test_retry_after_review_returns_same_run_and_keeps_review_state(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c, 'L2', 'keep')
    rec = rg_repo.seed_recommendation(run_id)
    assert review(c, run_id, rec['id'], 1, 'accept').status_code == 201
    before = state_of(rg_repo)
    retry = c.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'keep'})
    assert retry.status_code == 200 and retry.json()['run_id'] == run_id
    assert state_of(rg_repo) == before and len(rg_repo.runs) == 1


def test_retry_after_connection_loss_does_not_need_the_snapshot_file_again(rg_coach, rg_snap, rg_repo):
    """H03 mất kết nối: retry cùng mã nên trả bản nháp đã có, kể cả khi snapshot hiện tại đã đổi/mất."""
    c = rg_coach(COACH_A)
    run_id = create_run(c, 'L2', 'lost')
    rg_snap.write_text('{bad', encoding='utf-8')
    retry = c.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'lost'})
    assert retry.status_code == 200 and retry.json()['run_id'] == run_id and len(rg_repo.runs) == 1


def test_idempotency_key_is_not_shared_across_coaches_even_under_race(rg_coach, rg_snap, rg_repo):
    a = rg_coach(COACH_A).post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'shared'}).json()['run_id']
    b = rg_coach(COACH_B).post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'shared'})
    assert b.status_code == 201 and b.json()['run_id'] != a
    assert {r['user_id'] for r in rg_repo.runs.values()} == {COACH_A['id'], COACH_B['id']}


# --- (d) máy trạng thái: Python đối chiếu văn bản SQL ---

def _sql_allowed():
    return {state: tuple(re.findall(r"'(\w+)'", decisions)) for state, decisions in
            re.findall(r"when '(\w+)' then p_decision = any \(array\[([^\]]*)\]\)", SQL)}


def _sql_new_status():
    block = SQL.split('v_new_status := case p_decision', 1)[1].split('end;', 1)[0]
    mapping = dict(re.findall(r"when '(\w+)' then '(\w+)'", block))
    mapping[DECISIONS[-1]] = re.search(r"else '(\w+)'", block).group(1)  # nhánh else = edited
    return mapping


def test_sql_text_is_parsed_completely():
    allowed = _sql_allowed()
    assert set(allowed) == set(STATES) and _sql_new_status() == {
        'accept': 'accepted', 'reject': 'rejected', 'request_changes': 'changes_requested', 'edited': 'edited'}
    assert REVIEW_TRANSITIONS == allowed


@pytest.mark.parametrize('state', STATES)
@pytest.mark.parametrize('decision', DECISIONS)
def test_every_state_decision_pair_behaves_like_sql(rg_coach, rg_snap, rg_repo, state, decision):
    allowed, new_status = _sql_allowed()[state], _sql_new_status()[decision]
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    seed = {'review_status': None if state == 'pending' else state, 'version': 7}
    if state == 'edited':
        seed.update(is_edited=True, needs_rereview=True, content='bản sửa')
    rec = rg_repo.seed_recommendation(run_id, jev_score=None if state == 'edited' else {'grounded': 0.9}, **seed)
    before = state_of(rg_repo)
    extra = {'content': 'nội dung mới'} if decision == 'edited' else {}
    res = review(c, run_id, rec['id'], 7, decision, **extra)
    if decision in allowed:
        assert res.status_code == 201, res.text
        body = res.json()['recommendation']
        assert (body['review_status'], body['version']) == (new_status, 8)
        [audit] = rg_repo.reviews
        assert (audit['status_before'], audit['status_after'], audit['expected_version'], audit['new_version']) == \
            (state, new_status, 7, 8)
        if decision == 'edited':
            assert body['jev_score'] is None and body['is_edited'] and body['needs_rereview']
        elif state != 'edited':
            assert body['jev_score'] == {'grounded': 0.9}  # chỉ sửa tay mới bỏ điểm JEV
    else:
        assert res.status_code == 422 and res.json()['detail']['code'] == 'invalid_transition'
        assert sorted(res.json()['detail']['allowed_decisions']) == sorted(allowed)
        assert state_of(rg_repo) == before


@pytest.mark.parametrize('decision', DECISIONS)
def test_unknown_stored_status_allows_nothing_and_never_500s(rg_coach, rg_snap, rg_repo, decision):
    c = rg_coach(COACH_A, raise_server_exceptions=False)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id, review_status='weird_state')
    extra = {'content': 'x'} if decision == 'edited' else {}
    res = review(c, run_id, rec['id'], 1, decision, **extra)  # SQL: `else false`
    assert res.status_code == 422 and res.json()['detail']['code'] == 'invalid_transition'
    assert rg_repo.reviews == []


@pytest.mark.parametrize('version', [2, 5, 2_147_483_647])
def test_future_version_is_409_not_a_write(rg_coach, rg_snap, rg_repo, version):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id)
    res = review(c, run_id, rec['id'], version, 'accept')
    assert res.status_code == 409 and res.json()['detail']['code'] == 'version_conflict'
    assert res.json()['detail']['current_version'] == 1 and rg_repo.reviews == []


@pytest.mark.parametrize('retry', [
    {'decision': 'accept', 'comment': 'khác'}, {'decision': 'accept'}, {'decision': 'reject', 'comment': 'ok'}])
def test_only_an_identical_retry_is_replayed_any_difference_is_409(rg_coach, rg_snap, rg_repo, retry):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id)
    assert review(c, run_id, rec['id'], 1, 'accept', comment='ok').status_code == 201
    res = review(c, run_id, rec['id'], 1, **{**retry, 'decision': retry['decision']})
    assert res.status_code == 409 and res.json()['detail']['code'] == 'version_conflict'
    assert len(rg_repo.reviews) == 1  # SQL: replay cần cùng decision, comment, content


def test_edited_retry_with_different_content_is_409_not_replayed(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id, review_status='changes_requested', version=2)
    assert review(c, run_id, rec['id'], 2, 'edited', content='bản A').status_code == 201
    assert review(c, run_id, rec['id'], 2, 'edited', content='bản A').json()['replayed'] is True
    assert review(c, run_id, rec['id'], 2, 'edited', content='bản B').status_code == 409
    assert len(rg_repo.reviews) == 1 and rg_repo.recommendations[0]['content'] == 'bản A'


def test_two_tabs_conflict_then_reload_then_save_succeeds(rg_coach, rg_snap, rg_repo):
    """H05: tab 1 và tab 2 cùng tải version 1; tab 2 nhận 409, tải lại, lưu tiếp thành công."""
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id)
    tab1 = c.get(f'/api/analysis-runs/{run_id}').json()['recommendations'][0]
    tab2 = c.get(f'/api/analysis-runs/{run_id}').json()['recommendations'][0]
    assert tab1['version'] == tab2['version'] == 1
    assert review(c, run_id, rec['id'], tab1['version'], 'accept').status_code == 201
    conflict = review(c, run_id, rec['id'], tab2['version'], 'request_changes', comment='tab 2')
    assert conflict.status_code == 409
    detail = conflict.json()['detail']
    reloaded = c.get(detail['reload_url']).json()['recommendations'][0]
    assert reloaded['version'] == detail['current_version'] == 2 and reloaded['review_status'] == 'accepted'
    assert review(c, run_id, rec['id'], reloaded['version'], 'request_changes', comment='tab 2').status_code == 201
    assert [(r['status_before'], r['status_after'], r['expected_version'], r['new_version']) for r in rg_repo.reviews] == \
        [('pending', 'accepted', 1, 2), ('accepted', 'changes_requested', 2, 3)]


def test_audit_chain_is_contiguous_and_edit_never_inherits_jev(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id, content='gốc', jev_score={'grounded': 0.95})
    version = 1
    steps = [('request_changes', {}), ('edited', {'content': 'sửa lần 1'}), ('edited', {'content': 'sửa lần 2'}),
             ('request_changes', {}), ('edited', {'content': 'sửa lần 3'}), ('accept', {})]
    for decision, extra in steps:
        res = review(c, run_id, rec['id'], version, decision, comment=f'{decision}@{version}', **extra)
        assert res.status_code == 201, (decision, res.text)
        version += 1
    audits = rg_repo.reviews
    assert [a['new_version'] for a in audits] == list(range(2, 8))
    for prev, cur in zip(audits, audits[1:]):
        assert cur['status_before'] == prev['status_after'] and cur['expected_version'] == prev['new_version']
        assert cur['content_before'] == prev['content_after']
    assert audits[0]['content_before'] == 'gốc' and audits[-1]['content_after'] == 'sửa lần 3'
    final = c.get(f'/api/analysis-runs/{run_id}').json()['recommendations'][0]
    assert (final['review_status'], final['is_edited'], final['jev_score'], final['version']) == ('accepted', True, None, 7)
    assert [r['decision'] for r in c.get(f'/api/analysis-runs/{run_id}').json()['reviews']] == [s[0] for s in steps]


def test_concurrent_reviews_across_four_tabs_apply_exactly_once(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id)
    barrier = threading.Barrier(4, timeout=5)
    rg_repo.before_review = lambda rec_id, version: barrier.wait()
    decisions = ['accept', 'reject', 'request_changes', 'accept']

    def post(decision):
        return TestClient(app).post(f'/api/analysis-runs/{run_id}/reviews', json={
            'recommendation_id': rec['id'], 'version': 1, 'decision': decision})
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(post, decisions))
    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 1 and all(code in (200, 409) for code in codes if code != 201)
    assert len(rg_repo.reviews) == 1 and rg_repo.recommendations[0]['version'] == 2
    winner = next(r for r in results if r.status_code == 201).json()
    assert rg_repo.recommendations[0]['review_status'] == winner['recommendation']['review_status']


def test_review_validation_failure_is_422_and_never_touches_version(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rec = rg_repo.seed_recommendation(run_id)
    for bad in ({'decision': 'edited', 'content': 'x' * 4001}, {'decision': 'accept', 'comment': 'y' * 2001},
                {'decision': 'accept', 'version': '1; drop table'}, {'decision': 'accept', 'version': 1.5}):
        payload = {'recommendation_id': rec['id'], 'version': 1, **bad}
        assert c.post(f'/api/analysis-runs/{run_id}/reviews', json=payload).status_code == 422
    assert rg_repo.reviews == [] and rg_repo.recommendations[0]['version'] == 1
    assert json.dumps(rg_repo.recommendations[0], default=str)  # còn nguyên, tuần tự hoá được
