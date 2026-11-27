import copy
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api import analysis_runs as runs_api
from codebase.backend.api.run_repository import (
    DuplicateRequestError, InMemoryRunRepository, RepositoryError, SupabaseRunRepository, get_run_repository)
from codebase.backend.main import app
from codebase.backend.security import auth
from codebase.backend.security.auth import require_coach
from tests.test_dashboard import SNAP

COACH_A = {'id': '11111111-1111-1111-1111-111111111111', 'email': 'a@example.com'}
COACH_B = {'id': '22222222-2222-2222-2222-222222222222', 'email': 'b@example.com'}


@pytest.fixture
def snap_path(tmp_path, monkeypatch):
    path = tmp_path / 'agg.v2.json'
    path.write_text(json.dumps(SNAP), encoding='utf-8')
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


class Clock:
    def __init__(self):
        self.n = 0

    def __call__(self):
        self.n += 1
        return f'2026-11-27T10:00:{self.n:02d}.000000+00:00'


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


def _post(client, lesson_id='L1', request_id='req-1'):
    return client.post('/api/analysis-runs', json={'lesson_id': lesson_id, 'request_id': request_id})


def test_create_then_retry_returns_same_run(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    first = _post(c)
    assert first.status_code == 201 and first.json()['created'] is True
    body = first.json()
    assert body['status'] == 'draft' and body['ai_status'] == 'not_enabled' and body['snapshot_version'] == 'v2:t'
    stored = repo.runs[body['run_id']]
    assert stored['user_id'] == COACH_A['id']
    assert stored['metrics_snapshot']['lesson']['sample']['responses'] == 20
    again = _post(c)
    assert again.status_code == 200 and again.json()['run_id'] == body['run_id'] and again.json()['created'] is False
    assert len(repo.runs) == 1


def test_same_request_id_other_lesson_409(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    assert _post(c, 'L1').status_code == 201
    assert _post(c, 'L2').status_code == 409
    assert len(repo.runs) == 1


def test_same_request_id_is_scoped_per_owner(as_coach, snap_path, repo):
    a = _post(as_coach(COACH_A)).json()['run_id']
    b = _post(as_coach(COACH_B), 'L2').json()['run_id']
    assert a != b and repo.runs[b]['user_id'] == COACH_B['id']


def test_unknown_lesson_404_and_missing_snapshot_404(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    assert _post(c, 'NOPE').status_code == 404
    snap_path.unlink()
    assert _post(c, 'L1').status_code == 404
    assert repo.runs == {}


@pytest.mark.parametrize('payload', [
    {'lesson_id': 'L1', 'request_id': ''}, {'lesson_id': 'L1', 'request_id': '   '},
    {'lesson_id': 'L1', 'request_id': 'x' * 129}, {'lesson_id': 'L1', 'request_id': 'a\nb'},
    {'lesson_id': 'L1'}, {'lesson_id': '', 'request_id': 'r'},
    {'lesson_id': 'L1', 'request_id': 'r', 'user_id': COACH_B['id']},  # owner không nhận từ client
])
def test_invalid_body_422(as_coach, snap_path, repo, payload):
    assert as_coach(COACH_A).post('/api/analysis-runs', json=payload).status_code == 422
    assert repo.runs == {}


def test_request_id_128_chars_ok(as_coach, snap_path):
    assert _post(as_coach(COACH_A), request_id='x' * 128).status_code == 201


def test_retry_keeps_creation_time_snapshot(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    changed = copy.deepcopy(SNAP)
    changed['generated_at'] = 't2'
    changed['lessons']['L1']['sample']['responses'] = 999
    snap_path.write_text(json.dumps(changed), encoding='utf-8')
    assert _post(c).json()['snapshot_version'] == 'v2:t'
    detail = c.get(f'/api/analysis-runs/{run_id}').json()
    assert detail['snapshot']['data']['lesson']['sample']['responses'] == 20
    assert detail['snapshot']['data']['snapshot_version'] == 'v2:t'


def test_concurrent_creates_same_request_yield_one_run(snap_path, repo):
    barrier = threading.Barrier(2, timeout=5)  # cả hai đã qua find_by_request (None) trước khi insert
    repo.before_insert = lambda owner, row: barrier.wait()
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: runs_api.create_run(repo, COACH_A['id'], 'L1', 'race'), range(2)))
    assert len(repo.runs) == 1
    assert {r[0]['id'] for r in results} == set(repo.runs)
    assert sorted(r[1] for r in results) == [False, True]


def test_race_winner_with_other_lesson_gives_409(snap_path, repo):
    def concurrent_winner(owner, row):
        repo.before_insert = None
        repo.insert_run(owner, {**row, 'lesson_id': 'L2'})
    repo.before_insert = concurrent_winner
    with pytest.raises(runs_api.HTTPException) as err:
        runs_api.create_run(repo, COACH_A['id'], 'L1', 'race')
    assert err.value.status_code == 409 and len(repo.runs) == 1


def test_repository_failure_is_503(as_coach, snap_path, repo):
    def boom(*a, **kw):
        raise RepositoryError('x')
    repo.find_by_request = boom
    repo.list_runs = boom
    repo.get_run_detail = boom
    c = as_coach(COACH_A)
    assert _post(c).status_code == 503
    assert c.get('/api/analysis-runs').status_code == 503
    assert c.get('/api/analysis-runs/abc').status_code == 503


def test_cross_owner_detail_is_404_same_as_missing(as_coach, snap_path, repo):
    run_id = _post(as_coach(COACH_A)).json()['run_id']
    b = as_coach(COACH_B)
    other, missing = b.get(f'/api/analysis-runs/{run_id}'), b.get('/api/analysis-runs/00000000-0000-0000-0000-000000000000')
    assert other.status_code == missing.status_code == 404 and other.json() == missing.json()
    assert b.get('/api/analysis-runs').json()['items'] == []
    assert as_coach(COACH_A).get(f'/api/analysis-runs/{run_id}').status_code == 200


def test_list_filters_and_keyset_pagination(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    ids = [_post(c, 'L1' if i % 2 == 0 else 'L2', f'r{i}').json()['run_id'] for i in range(5)]
    tie = '2026-11-27T10:00:03.000000+00:00'  # đồng created_at: id là khoá phụ
    repo.seed_run(COACH_A['id'], lesson_id='L1', created_at=tie)
    repo.seed_run(COACH_A['id'], lesson_id='L1', created_at=tie)
    repo.seed_run(COACH_B['id'], lesson_id='L1')
    seen, cursor = [], None
    while True:
        params = {'limit': 2, **({'cursor': cursor} if cursor else {})}
        page = c.get('/api/analysis-runs', params=params).json()
        assert len(page['items']) <= 2
        seen += page['items']
        cursor = page['next_cursor']
        if not cursor:
            break
    keys = [(i['created_at'], i['run_id']) for i in seen]
    assert keys == sorted(keys, reverse=True) and len(set(keys)) == len(keys) == 7
    assert set(ids) <= {i['run_id'] for i in seen}
    l2 = c.get('/api/analysis-runs', params={'lesson_id': 'L2'}).json()['items']
    assert {i['run_id'] for i in l2} == {ids[1], ids[3]}
    legacy = c.get('/api/analysis-runs', params={'ai_status': 'not_recorded'}).json()['items']
    assert len(legacy) == 2 and all(i['status'] == 'pending' for i in legacy)
    assert len(c.get('/api/analysis-runs', params={'status': 'draft'}).json()['items']) == 5
    assert len(c.get('/api/analysis-runs', params={'ai_status': 'not_enabled'}).json()['items']) == 5


@pytest.mark.parametrize('params', [{'limit': 0}, {'limit': 101}])
def test_list_limit_bounds_422(as_coach, params):
    assert as_coach(COACH_A).get('/api/analysis-runs', params=params).status_code == 422


@pytest.mark.parametrize('params', [{'cursor': 'not-base64!'}, {'cursor': 'e30'}, {'ai_status': 'bogus'},
                                    {'status': 'DROP TABLE'}])
def test_list_bad_params_422(as_coach, params):
    assert as_coach(COACH_A).get('/api/analysis-runs', params=params).status_code == 422


def test_legacy_draft_without_metadata_opens_and_flags_missing(as_coach, repo):
    legacy = repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot={})
    repo.recommendations.append({'id': 'r1', 'analysis_run_id': legacy['id'], 'kc_code': 'K1', 'priority': 1,
                                 'content': 'x', 'citations': [], 'review_status': None})
    body = as_coach(COACH_A).get(f"/api/analysis-runs/{legacy['id']}").json()
    assert body['ai_status'] is None and body['snapshot_version'] is None and body['request_id'] is None
    assert {'ai_status', 'snapshot_version', 'request_id', 'metrics_snapshot'} <= set(body['not_recorded'])
    assert body['not_recorded_label'] == 'chưa được ghi nhận'
    assert body['snapshot'] == {'format': 'not_recorded', 'data': None, 'notice': 'Snapshot số liệu chưa được ghi nhận.'}
    assert body['recommendations'][0]['not_recorded'] == ['review_status']
    assert body['evaluations'] == [] and body['reviews'] == []


def test_legacy_snapshot_format_returned_as_is(as_coach, repo):
    old = {'L1': [{'kc_code': 'K1', 'incorrect_rate': 0.4}]}
    legacy = repo.seed_run(COACH_A['id'], metrics_snapshot=old)
    snap = as_coach(COACH_A).get(f"/api/analysis-runs/{legacy['id']}").json()['snapshot']
    assert snap['format'] == 'legacy' and snap['data'] == old


def test_detail_includes_reviews_in_order(as_coach, snap_path, repo):
    run_id = _post(as_coach(COACH_A)).json()['run_id']
    repo.reviews += [{'id': 'b', 'run_id': run_id, 'at': '2026-11-27T11:00:02Z', 'decision': 'reject'},
                     {'id': 'a', 'run_id': run_id, 'at': '2026-11-27T11:00:01Z', 'decision': 'accept'}]
    body = as_coach(COACH_A).get(f'/api/analysis-runs/{run_id}').json()
    assert [r['decision'] for r in body['reviews']] == ['accept', 'reject'] and body['not_recorded'] == []


def test_requires_auth_401_before_repository_config(monkeypatch):
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    c = TestClient(app)
    assert c.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'r'}).status_code == 401
    assert c.get('/api/analysis-runs').status_code == 401
    assert c.get('/api/analysis-runs/x').status_code == 401


def test_not_allowlisted_403(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public')
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': COACH_A['id']})
        return httpx.Response(200, json=False)
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    c, h = TestClient(app), {'Authorization': 'Bearer x'}
    assert c.get('/api/analysis-runs', headers=h).status_code == 403
    assert c.post('/api/analysis-runs', headers=h, json={'lesson_id': 'L1', 'request_id': 'r'}).status_code == 403


def test_missing_service_role_is_503_and_not_exposed(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    app.dependency_overrides[require_coach] = lambda: COACH_A
    try:
        c = TestClient(app)
        assert c.get('/api/analysis-runs').status_code == 503
        monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'srv-secret-value')
        assert 'srv-secret-value' not in c.get('/api/config').text
    finally:
        app.dependency_overrides.clear()


# --- SupabaseRunRepository qua MockTransport (không gọi mạng thật) ---

def _supabase(handler):
    client_type = httpx.Client
    return SupabaseRunRepository('https://example.test', 'srv-secret-value',
                                 client_factory=lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))


def test_supabase_every_query_filters_owner_and_uses_service_key():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[{'id': '33333333-3333-3333-3333-333333333333'}]
                              if request.url.path.endswith('analysis_runs') else [])
    repo = _supabase(handler)
    repo.find_by_request(COACH_A['id'], 'r1')
    repo.list_runs(COACH_A['id'], lesson_id='L1', ai_status='not_recorded', limit=3,
                   after=('2026-11-27T10:00:00+00:00', '33333333-3333-3333-3333-333333333333'))
    repo.get_run_detail(COACH_A['id'], '33333333-3333-3333-3333-333333333333')
    run_queries = [c for c in calls if c.url.path.endswith('/analysis_runs')]
    assert len(run_queries) == 3
    for c in run_queries:
        assert parse_qs(c.url.query.decode())['user_id'] == [f"eq.{COACH_A['id']}"]
        assert '*' not in parse_qs(c.url.query.decode())['select'][0]
    listing = parse_qs(run_queries[1].url.query.decode())
    assert listing['ai_status'] == ['is.null'] and listing['order'] == ['created_at.desc,id.desc']
    assert listing['or'] == ['(created_at.lt."2026-11-27T10:00:00+00:00",and(created_at.eq."2026-11-27T10:00:00+00:00",'
                             'id.lt."33333333-3333-3333-3333-333333333333"))']
    assert all(c.headers['apikey'] == 'srv-secret-value' for c in calls)
    assert {c.url.path.rsplit('/', 1)[-1] for c in calls} == {'analysis_runs', 'recommendations',
                                                             'evaluation_results', 'recommendation_reviews'}


def test_supabase_detail_skips_children_when_not_owned():
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[])
    assert _supabase(handler).get_run_detail(COACH_B['id'], '33333333-3333-3333-3333-333333333333') is None
    assert len(calls) == 1
    assert _supabase(handler).get_run(COACH_B['id'], 'not-a-uuid') is None and len(calls) == 1


def test_supabase_unique_violation_maps_to_duplicate_and_errors_hide_key():
    repo = _supabase(lambda r: httpx.Response(409, json={'code': '23505', 'message': 'dup'}))
    with pytest.raises(DuplicateRequestError):
        repo.insert_run(COACH_A['id'], {'lesson_id': 'L1', 'request_id': 'r'})
    def down(request):
        raise httpx.ConnectTimeout('timeout', request=request)
    with pytest.raises(RepositoryError) as err:
        _supabase(down).find_by_request(COACH_A['id'], 'r')
    assert 'srv-secret-value' not in repr(err.value) and err.value.__cause__ is None
    with pytest.raises(RepositoryError):
        _supabase(lambda r: httpx.Response(500, text='x')).list_runs(COACH_A['id'])
