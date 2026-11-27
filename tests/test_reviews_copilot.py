import copy
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api import copilot as copilot_api
from codebase.backend.api import reviews as reviews_api
from codebase.backend.api.run_repository import (
    REVIEW_TRANSITIONS, InMemoryRunRepository, RepositoryError, SupabaseRunRepository, get_run_repository)
from codebase.backend.main import app
from codebase.backend.security import auth
from codebase.backend.security.auth import require_coach
from tests.test_analysis_runs import COACH_A, COACH_B, Clock
from tests.test_dashboard import SNAP

MIGRATION = Path(__file__).resolve().parents[1] / 'supabase/migrations/20261127000004_review_recommendation_rpc.sql'
RUN_UUID = '33333333-3333-3333-3333-333333333333'
REC_UUID = '44444444-4444-4444-4444-444444444444'


def _lesson_snapshot():
    snap = copy.deepcopy(SNAP)
    l2 = snap['lessons']['L2']
    l2['kcs'] = [
        {'kc_code': 'K1', 'status': 'ok', 'graded_count': 20, 'learner_count': 15, 'incorrect_rate': 0.4,
         'delta_vs_previous_pp': -10.0},
        {'kc_code': 'K3', 'status': 'ok', 'graded_count': 12, 'learner_count': 9, 'incorrect_rate': 0.4,
         'delta_vs_previous_pp': None},
        {'kc_code': 'K4', 'status': 'ok', 'graded_count': 30, 'learner_count': 20, 'incorrect_rate': 0.1,
         'delta_vs_previous_pp': 5.0},
        {'kc_code': 'K2', 'status': 'insufficient_sample', 'graded_count': 3, 'learner_count': 3,
         'incorrect_rate': 1.0, 'delta_vs_previous_pp': None},
        {'kc_code': 'K5', 'status': 'no_graded', 'graded_count': 0, 'ungraded_count': 4, 'incorrect_rate': None},
    ]
    l2['priority'] = [{**l2['kcs'][0], 'rank': 1}, {**l2['kcs'][1], 'rank': 1}]
    return snap


@pytest.fixture
def snap_path(tmp_path, monkeypatch):
    path = tmp_path / 'agg.v2.json'
    path.write_text(json.dumps(_lesson_snapshot()), encoding='utf-8')
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


@pytest.fixture
def repo():
    return InMemoryRunRepository(clock=Clock())


@pytest.fixture
def as_coach(repo):
    current = {'user': COACH_A}
    app.dependency_overrides[require_coach] = lambda: current['user']
    app.dependency_overrides[get_run_repository] = lambda: repo

    def switch(user):
        current['user'] = user
        return TestClient(app)
    yield switch
    app.dependency_overrides.clear()


def _create(client, lesson='L2', request_id='req-1'):
    res = client.post('/api/analysis-runs', json={'lesson_id': lesson, 'request_id': request_id})
    assert res.status_code == 201
    return res.json()['run_id']


@pytest.fixture
def run_rec(as_coach, snap_path, repo):
    run_id = _create(as_coach(COACH_A))
    rec = repo.seed_recommendation(run_id, content='Ôn lại K1', jev_score={'grounded': 0.9})
    return run_id, rec


def _review(client, run_id, rec_id, version, decision, **extra):
    return client.post(f'/api/analysis-runs/{run_id}/reviews',
                       json={'recommendation_id': rec_id, 'version': version, 'decision': decision, **extra})


# --- /reviews ---

@pytest.mark.parametrize('decision,status', [('accept', 'accepted'), ('reject', 'rejected'),
                                             ('request_changes', 'changes_requested')])
def test_review_decisions_update_status_and_audit(as_coach, run_rec, repo, decision, status):
    run_id, rec = run_rec
    res = _review(as_coach(COACH_A), run_id, rec['id'], 1, decision, comment='ok')
    assert res.status_code == 201
    body = res.json()
    assert body['replayed'] is False
    assert body['recommendation']['review_status'] == status and body['recommendation']['version'] == 2
    assert body['recommendation']['jev_score'] == {'grounded': 0.9}  # không sửa nội dung -> giữ JEV
    [audit] = repo.reviews
    assert audit == {**audit, 'actor_id': COACH_A['id'], 'actor_email': COACH_A['email'], 'decision': decision,
                     'expected_version': 1, 'new_version': 2, 'status_before': 'pending', 'status_after': status,
                     'content_before': 'Ôn lại K1', 'content_after': 'Ôn lại K1', 'comment': 'ok', 'run_id': run_id}
    assert audit['at'] and 'actor_email' not in body['review']


def test_request_changes_then_edited_drops_jev_and_needs_rereview(as_coach, run_rec, repo):
    run_id, rec = run_rec
    c = as_coach(COACH_A)
    assert _review(c, run_id, rec['id'], 1, 'request_changes').status_code == 201
    blocked = _review(c, run_id, rec['id'], 2, 'accept')  # không được accept bản gốc sau yêu cầu sửa
    assert blocked.status_code == 422 and blocked.json()['detail']['code'] == 'invalid_transition'
    assert blocked.json()['detail']['allowed_decisions'] == ['edited', 'reject']
    res = _review(c, run_id, rec['id'], 2, 'edited', content='Ôn K1 bằng 3 ví dụ', comment='sửa tay')
    assert res.status_code == 201
    r = res.json()['recommendation']
    assert (r['review_status'], r['is_edited'], r['needs_rereview'], r['jev_score'], r['version'], r['content']) == \
        ('edited', True, True, None, 3, 'Ôn K1 bằng 3 ví dụ')
    audit = repo.reviews[-1]
    assert (audit['content_before'], audit['content_after'], audit['status_before'], audit['needs_rereview']) == \
        ('Ôn lại K1', 'Ôn K1 bằng 3 ví dụ', 'changes_requested', True)
    # Duyệt lại bản sửa: accepted nhưng vẫn không mang JEV, vẫn đánh dấu chưa kiểm định lại.
    again = _review(c, run_id, rec['id'], 3, 'accept').json()['recommendation']
    assert (again['review_status'], again['is_edited'], again['jev_score'], again['needs_rereview']) == \
        ('accepted', True, None, True)
    assert len(repo.reviews) == 3
    detail = c.get(f'/api/analysis-runs/{run_id}').json()
    assert [v['decision'] for v in detail['reviews']] == ['request_changes', 'edited', 'accept']


def test_edited_not_allowed_from_pending(as_coach, run_rec, repo):
    run_id, rec = run_rec
    res = _review(as_coach(COACH_A), run_id, rec['id'], 1, 'edited', content='x')
    assert res.status_code == 422 and res.json()['detail']['code'] == 'invalid_transition'
    assert repo.reviews == [] and repo.recommendations[0]['version'] == 1


@pytest.mark.parametrize('extra', [
    {'decision': 'edited'}, {'decision': 'edited', 'content': '   '}, {'decision': 'accept', 'content': 'x'},
    {'decision': 'approve'}, {'decision': 'accept', 'version': 0}, {'decision': 'accept', 'comment': 'x' * 2001},
    {'decision': 'edited', 'content': 'x' * 4001}, {'decision': 'accept', 'actor_id': COACH_B['id']},
    {'decision': 'accept', 'comment': 'a\x00b'}, {'decision': 'accept', 'recommendation_id': ''},
])
def test_review_body_validation_422(as_coach, run_rec, repo, extra):
    run_id, rec = run_rec
    payload = {'recommendation_id': rec['id'], 'version': 1, **extra}
    res = as_coach(COACH_A).post(f'/api/analysis-runs/{run_id}/reviews', json=payload)
    assert res.status_code == 422 and repo.reviews == []


def test_stale_version_409_with_reload_payload(as_coach, run_rec, repo):
    run_id, rec = run_rec
    c = as_coach(COACH_A)
    assert _review(c, run_id, rec['id'], 1, 'accept').status_code == 201
    stale = _review(c, run_id, rec['id'], 1, 'reject')
    assert stale.status_code == 409
    d = stale.json()['detail']
    assert d['code'] == 'version_conflict' and d['current_version'] == 2 and d['expected_version'] == 1
    assert d['recommendation']['review_status'] == 'accepted' and d['reload_url'] == f'/api/analysis-runs/{run_id}'
    assert len(repo.reviews) == 1


def test_exact_retry_is_replayed_not_duplicated(as_coach, run_rec, repo):
    run_id, rec = run_rec
    c = as_coach(COACH_A)
    first = _review(c, run_id, rec['id'], 1, 'accept', comment='ok')
    retry = _review(c, run_id, rec['id'], 1, 'accept', comment='ok')
    assert retry.status_code == 200 and retry.json()['replayed'] is True
    assert retry.json()['review']['id'] == first.json()['review']['id'] and len(repo.reviews) == 1


def test_concurrent_reviews_same_version_only_one_wins(as_coach, run_rec, repo):
    run_id, rec = run_rec
    barrier = threading.Barrier(2, timeout=5)  # cả hai request đã đọc version 1 trước khi vào transaction
    repo.before_review = lambda rec_id, version: barrier.wait()
    bodies = [reviews_api.ReviewBody(recommendation_id=rec['id'], version=1, decision=d)
              for d in ('accept', 'reject')]

    def attempt(body):
        try:
            return reviews_api.submit_review(repo, COACH_A, run_id, body)[0]['recommendation']['review_status']
        except reviews_api.HTTPException as err:
            return err.status_code
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(attempt, bodies))
    assert sorted(map(str, results)) in (['409', 'accepted'], ['409', 'rejected'])
    assert len(repo.reviews) == 1 and repo.recommendations[0]['version'] == 2
    assert repo.recommendations[0]['review_status'] == repo.reviews[0]['status_after']


def test_failure_before_commit_rolls_back_both(as_coach, run_rec, repo):
    run_id, rec = run_rec
    def boom(updated, review):
        raise RepositoryError('audit_insert_failed')
    repo.before_review_commit = boom
    res = _review(as_coach(COACH_A), run_id, rec['id'], 1, 'accept')
    assert res.status_code == 503 and repo.reviews == []
    assert repo.recommendations[0]['version'] == 1 and repo.recommendations[0]['review_status'] is None


def test_review_cross_owner_and_other_run_404(as_coach, run_rec, repo):
    run_id, rec = run_rec
    b = as_coach(COACH_B)
    other = _review(b, run_id, rec['id'], 1, 'accept')
    missing = _review(b, '00000000-0000-0000-0000-000000000000', rec['id'], 1, 'accept')
    assert other.status_code == missing.status_code == 404 and other.json() == missing.json()
    b_run = _create(b, 'L2', 'req-b')  # B sở hữu run khác, nhưng đề xuất thuộc run của A
    assert _review(b, b_run, rec['id'], 1, 'accept').status_code == 404
    a = as_coach(COACH_A)
    a_other = _create(a, 'L1', 'req-2')
    assert _review(a, a_other, rec['id'], 1, 'accept').status_code == 404  # đề xuất không thuộc run này
    assert repo.reviews == [] and repo.recommendations[0]['version'] == 1


def test_transitions_match_sql_function():
    sql = MIGRATION.read_text(encoding='utf-8')
    found = {state: tuple(re.findall(r"'(\w+)'", decisions)) for state, decisions in
             re.findall(r"when '(\w+)' then p_decision = any \(array\[([^\]]*)\]\)", sql)}
    assert found == REVIEW_TRANSITIONS


def test_migration_rpc_privileges_and_atomic_guards():
    sql = MIGRATION.read_text(encoding='utf-8')
    assert 'security invoker' in sql and "set search_path = ''" in sql
    assert re.search(r'revoke execute on function public\.review_recommendation\([^)]*\)\s+from public, anon, '
                     r'authenticated;', sql)
    assert re.search(r'grant execute on function public\.review_recommendation\([^)]*\)\s+to service_role;', sql)
    assert 'for update' in sql and 'version = p_expected_version' in sql
    assert 'jev_score = case when v_edited then null' in sql
    assert not re.search(r'\b(drop table|truncate|delete from)\b', sql.split('-- DOWN:')[1].split('\n\n', 1)[1],
                         re.IGNORECASE)


def test_supabase_apply_review_posts_rpc_with_session_actor():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={'outcome': 'version_conflict', 'recommendation': {'version': 3}})
    client_type = httpx.Client
    repo = SupabaseRunRepository('https://example.test', 'srv-secret-value',
                                 client_factory=lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    out = repo.apply_review(COACH_A['id'], RUN_UUID, recommendation_id=REC_UUID, expected_version=2,
                            decision='edited', comment=None, content='mới', actor_email='a@example.com')
    assert out['outcome'] == 'version_conflict'
    [call] = calls
    assert call.method == 'POST' and call.url.path == '/rest/v1/rpc/review_recommendation'
    assert json.loads(call.content) == {
        'p_run_id': RUN_UUID, 'p_recommendation_id': REC_UUID, 'p_expected_version': 2, 'p_decision': 'edited',
        'p_comment': None, 'p_content': 'mới', 'p_actor_id': COACH_A['id'], 'p_actor_email': 'a@example.com'}
    assert call.headers['apikey'] == 'srv-secret-value'
    assert repo.apply_review(COACH_A['id'], RUN_UUID, recommendation_id='bad', expected_version=1, decision='accept',
                             comment=None, content=None, actor_email=None) == {'outcome': 'not_found'}
    assert len(calls) == 1
    for bad in (httpx.Response(500, text='x'), httpx.Response(200, json={'outcome': 'weird'}),
                httpx.Response(200, json={'outcome': 'ok'})):
        broken = SupabaseRunRepository('https://example.test', 'k', client_factory=lambda **kw: client_type(
            transport=httpx.MockTransport(lambda r, b=bad: b), **kw))
        with pytest.raises(RepositoryError):
            broken.apply_review(COACH_A['id'], RUN_UUID, recommendation_id=REC_UUID, expected_version=1,
                                decision='accept', comment=None, content=None, actor_email=None)


# --- /copilot ---

def _copilot(client, run_id, action, kc_code=None):
    body = {'action': action, **({'kc_code': kc_code} if kc_code is not None else {})}
    return client.post(f'/api/analysis-runs/{run_id}/copilot', json=body)


def test_explain_priority_rank_with_tie_and_evidence(as_coach, snap_path):
    c = as_coach(COACH_A)
    run_id = _create(c)
    body = _copilot(c, run_id, 'explain_priority', 'K1').json()
    assert body['status'] == 'ok' and body['source'] == 'stored_snapshot' and body['generated_by'] == 'code'
    assert 'hạng 1' in body['message'] and '40.0%' in body['message'] and 'K3' in body['message']
    assert {'kc_code': 'K1', 'field': 'kcs.incorrect_rate', 'value': 0.4} in body['evidence']
    assert {'kc_code': 'K3', 'field': 'priority.rank', 'value': 1} in body['evidence']
    assert body['snapshot_version'] == 'v2:t'


@pytest.mark.parametrize('kc,expect,field', [
    ('K2', 'dưới ngưỡng 10 lượt', 'min_sample'), ('K5', 'mẫu số 0', 'kcs.ungraded_count'),
    ('K4', 'ngoài nhóm ưu tiên', 'priority.incorrect_rate')])
def test_explain_priority_non_ranked_kcs(as_coach, snap_path, kc, expect, field):
    c = as_coach(COACH_A)
    body = _copilot(c, _create(c), 'explain_priority', kc).json()
    assert expect in body['message'] and field in {e['field'] for e in body['evidence']}


def test_compare_previous_lesson_and_kc(as_coach, snap_path):
    c = as_coach(COACH_A)
    run_id = _create(c)
    lesson = _copilot(c, run_id, 'compare_previous').json()
    assert lesson['status'] == 'ok' and 'giảm 30.0 điểm phần trăm' in lesson['message'] and 'L1' in lesson['message']
    assert {'kc_code': None, 'field': 'delta_vs_previous_pp', 'value': -30.0} in lesson['evidence']
    kc = _copilot(c, run_id, 'compare_previous', 'K1').json()
    assert kc['status'] == 'ok' and 'giảm 10.0' in kc['message']
    missing_kc = _copilot(c, run_id, 'compare_previous', 'K3').json()
    assert missing_kc['status'] == 'insufficient_comparison_data'


def test_compare_previous_without_previous_lesson(as_coach, snap_path):
    c = as_coach(COACH_A)
    body = _copilot(c, _create(c, 'L1'), 'compare_previous').json()
    assert body['status'] == 'insufficient_comparison_data' and body['evidence'] == []


def test_copilot_uses_stored_snapshot_when_current_changes(as_coach, snap_path, monkeypatch):
    c = as_coach(COACH_A)
    run_id = _create(c)
    before = _copilot(c, run_id, 'explain_priority', 'K1').json()
    changed = _lesson_snapshot()
    changed['generated_at'] = 't2'
    changed['lessons']['L2']['kcs'] = [{'kc_code': 'K9', 'status': 'ok', 'graded_count': 99, 'incorrect_rate': 0.9}]
    changed['lessons']['L2']['delta_vs_previous_pp'] = 50.0
    snap_path.write_text(json.dumps(changed), encoding='utf-8')
    def forbidden():
        raise AssertionError('copilot không được đọc snapshot hiện tại')
    monkeypatch.setattr('codebase.backend.analytics.snapshot.read_snapshot_v2', forbidden)
    monkeypatch.setattr('codebase.backend.api.analysis_runs.read_snapshot_v2', forbidden)
    assert _copilot(c, run_id, 'explain_priority', 'K1').json() == before
    assert 'giảm 30.0' in _copilot(c, run_id, 'compare_previous').json()['message']
    assert _copilot(c, run_id, 'explain_priority', 'K9').json()['detail']['code'] == 'kc_not_in_snapshot'


@pytest.mark.parametrize('action,kc,code', [
    ('explain_priority', None, 'kc_required'), ('explain_priority', 'NOPE', 'kc_not_in_snapshot'),
    ('compare_previous', 'NOPE', 'kc_not_in_snapshot'), ('recheck_questions', None, 'kc_required'),
    ('recheck_questions', 'NOPE', 'kc_not_in_snapshot')])
def test_copilot_kc_validation_422(as_coach, snap_path, action, kc, code):
    c = as_coach(COACH_A)
    res = _copilot(c, _create(c), action, kc)
    assert res.status_code == 422 and res.json()['detail']['code'] == code


@pytest.mark.parametrize('body', [{'action': 'free_chat'}, {'action': 'explain_priority', 'kc_code': 'K1', 'x': 1},
                                  {}, {'action': 'explain_priority', 'kc_code': ''}])
def test_copilot_unknown_action_or_extra_422(as_coach, snap_path, body):
    c = as_coach(COACH_A)
    assert c.post(f'/api/analysis-runs/{_create(c)}/copilot', json=body).status_code == 422


@pytest.mark.parametrize('action,kc', [('review_plan_15m', None), ('recheck_questions', 'K1')])
def test_ai_actions_blocked_by_server_gate(as_coach, snap_path, action, kc):
    c = as_coach(COACH_A)
    res = _copilot(c, _create(c), action, kc)
    assert res.status_code == 409
    d = res.json()['detail']
    assert d['code'] == 'ai_unavailable' and {'kb_missing', 'jev_uncalibrated'} <= set(d['reasons'])
    assert 'message' in d and 'evidence' not in d


def test_ai_gate_stays_closed_even_with_kb_and_jev_config(tmp_path):
    kb, jev = tmp_path / 'kb.json', tmp_path / 'jev.json'
    kb.write_text('{}'), jev.write_text('{}')
    gate = copilot_api.ai_gate({'ai_status': 'ready'}, {'LESSON_KB_PATH': str(kb), 'JEV_CALIBRATION_PATH': str(jev)})
    assert gate.open is False and gate.reasons == ('generation_not_enabled',)
    closed = copilot_api.ai_gate({'ai_status': 'not_enabled'}, {'LESSON_KB_PATH': str(tmp_path / 'missing')})
    assert closed.reasons == ('kb_missing', 'jev_uncalibrated', 'run_ai_not_ready', 'generation_not_enabled')


def test_copilot_legacy_snapshot_422_and_cross_owner_404(as_coach, snap_path, repo):
    legacy = repo.seed_run(COACH_A['id'], metrics_snapshot={'L1': []})
    c = as_coach(COACH_A)
    assert _copilot(c, legacy['id'], 'compare_previous').json()['detail']['code'] == 'snapshot_unavailable'
    run_id = _create(c)
    b = as_coach(COACH_B)
    other = _copilot(b, run_id, 'compare_previous')
    missing = _copilot(b, '00000000-0000-0000-0000-000000000000', 'compare_previous')
    assert other.status_code == missing.status_code == 404 and other.json() == missing.json()


def test_copilot_module_does_not_call_model():
    import ast
    tree = ast.parse(Path(copilot_api.__file__).read_text(encoding='utf-8'))
    modules = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    modules |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not {m for m in modules if re.search(r'langfuse|openai|httpx|codebase\.ai|agents|liquid', m or '')}
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert 'call_model' not in names and 'read_snapshot_v2' not in names


# --- 401 / 403 ---

def test_reviews_and_copilot_require_auth_401():
    c = TestClient(app)
    assert _review(c, 'x', 'y', 1, 'accept').status_code == 401
    assert _copilot(c, 'x', 'compare_previous').status_code == 401


def test_reviews_and_copilot_not_allowlisted_403(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public')
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': COACH_A['id']})
        return httpx.Response(200, json=False)
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    c, h = TestClient(app), {'Authorization': 'Bearer x'}
    assert c.post('/api/analysis-runs/x/reviews', headers=h,
                  json={'recommendation_id': 'r', 'version': 1, 'decision': 'accept'}).status_code == 403
    assert c.post('/api/analysis-runs/x/copilot', headers=h, json={'action': 'compare_previous'}).status_code == 403
