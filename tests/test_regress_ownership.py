"""Hồi quy quyền sở hữu xuyên endpoint và bảo vệ khoá service role (plan 001 step 10, mục a và f).

Spec: "ID báo cáo không tồn tại hoặc không thuộc coach trả 404"; "luôn kiểm sở hữu"; credential đặc quyền chỉ ở backend.
"""
import base64
import json
import logging
from pathlib import Path
from urllib.parse import parse_qsl, quote

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api.run_repository import get_run_repository
from codebase.backend.main import app
from codebase.backend.security.auth import require_coach
from tests.regression_support import (  # noqa: F401
    MISSING_UUID, SERVICE_KEY, copilot, create_run, review, rg_coach, rg_repo, rg_snap, state_of,
    supabase_repo_override)
from tests.test_analysis_runs import COACH_A, COACH_B

ROOT = Path(__file__).resolve().parents[1]
RUN_UUID = '33333333-3333-3333-3333-333333333333'

# Mỗi ca là một thao tác của coach B lên run của coach A. Body hợp lệ về hình dạng để không bị 422 che mất kiểm tra sở hữu.
CROSS_OWNER_CALLS = {
    'detail': lambda c, run, rec: c.get(f'/api/analysis-runs/{run}'),
    'export': lambda c, run, rec: c.get(f'/api/analysis-runs/{run}/export'),
    'copilot_numeric': lambda c, run, rec: copilot(c, run, 'compare_previous'),
    'copilot_kc_unknown': lambda c, run, rec: copilot(c, run, 'explain_priority', 'KHONG_CO'),
    'copilot_ai_action_gate_closed': lambda c, run, rec: copilot(c, run, 'review_plan_15m'),
    'copilot_ai_recheck': lambda c, run, rec: copilot(c, run, 'recheck_questions', 'K1'),
    'review_accept': lambda c, run, rec: review(c, run, rec, 1, 'accept', comment='xâm nhập'),
    'review_stale_version': lambda c, run, rec: review(c, run, rec, 99, 'accept'),
    'review_invalid_transition': lambda c, run, rec: review(c, run, rec, 1, 'edited', content='ghi đè'),
}


@pytest.mark.parametrize('name', sorted(CROSS_OWNER_CALLS))
def test_cross_owner_is_uniform_404_without_leak_or_side_effect(rg_coach, rg_snap, rg_repo, name):
    a = rg_coach(COACH_A)
    run_id = create_run(a)
    rec = rg_repo.seed_recommendation(run_id, content='NỘI DUNG RIÊNG TƯ CỦA A', jev_score={'grounded': 0.9})
    before = state_of(rg_repo)
    call = CROSS_OWNER_CALLS[name]
    b = rg_coach(COACH_B)
    other, missing = call(b, run_id, rec['id']), call(b, MISSING_UUID, rec['id'])
    assert other.status_code == 404 and missing.status_code == 404
    assert other.json() == missing.json()  # không phân biệt "của người khác" với "không tồn tại"
    for secret in ('NỘI DUNG RIÊNG TƯ', 'version_conflict', 'ai_unavailable', 'invalid_transition', 'kc_not_in_snapshot',
                   COACH_A['email'], COACH_A['id'], 'L2'):
        assert secret not in other.text
    assert 'attachment' not in other.headers.get('content-disposition', '')
    assert state_of(rg_repo) == before  # không đổi version, không audit, không run mới
    assert b.get('/api/analysis-runs').json()['items'] == []
    assert rg_coach(COACH_A).get(f'/api/analysis-runs/{run_id}').status_code == 200


def test_recommendation_of_another_run_is_indistinguishable_from_unknown_recommendation(rg_coach, rg_snap, rg_repo):
    a, b = rg_coach(COACH_A), None
    run_a = create_run(a, 'L2', 'req-a')
    other_run_a = create_run(a, 'L1', 'req-a2')
    rec_a = rg_repo.seed_recommendation(run_a, content='của A')
    b = rg_coach(COACH_B)
    run_b = create_run(b, 'L2', 'req-b')
    rec_b = rg_repo.seed_recommendation(run_b, content='của B')
    before = state_of(rg_repo)
    unknown = review(b, run_b, MISSING_UUID, 1, 'accept')
    assert unknown.status_code == 404
    # run_id của B khớp nhưng recommendation_id thuộc run (và owner) khác.
    stolen = review(b, run_b, rec_a['id'], 1, 'accept')
    assert stolen.status_code == 404 and stolen.json() == unknown.json()
    # Cùng chủ sở hữu A nhưng đề xuất thuộc run khác: cũng 404 và không đổi gì.
    a = rg_coach(COACH_A)
    cross_run = review(a, other_run_a, rec_a['id'], 1, 'reject')
    assert cross_run.status_code == 404 and cross_run.json() == unknown.json()
    # Đảo lại: A dùng run của mình nhưng đề xuất của B.
    assert review(a, run_a, rec_b['id'], 1, 'accept').status_code == 404
    assert state_of(rg_repo) == before
    # Đường đúng vẫn hoạt động: chỉ bộ ba (owner, run, recommendation) khớp mới ghi được.
    assert review(a, run_a, rec_a['id'], 1, 'accept').status_code == 201


def test_review_audit_actor_comes_from_session_not_payload(rg_coach, rg_snap, rg_repo):
    a = rg_coach(COACH_A)
    run_id = create_run(a)
    rec = rg_repo.seed_recommendation(run_id)
    res = a.post(f'/api/analysis-runs/{run_id}/reviews', json={
        'recommendation_id': rec['id'], 'version': 1, 'decision': 'accept', 'actor_id': COACH_B['id'],
        'actor_email': COACH_B['email']})
    assert res.status_code == 422 and rg_repo.reviews == []
    assert review(a, run_id, rec['id'], 1, 'accept').status_code == 201
    assert rg_repo.reviews[0]['actor_id'] == COACH_A['id'] and rg_repo.reviews[0]['actor_email'] == COACH_A['email']


# --- Injection qua lesson_id / status / ai_status / cursor / run_id (kho Supabase thật qua MockTransport) ---

LESSON_PAYLOADS = ["L1' or '1'='1", 'L1&user_id=neq.x', 'L1,user_id.neq.0', 'x&select=*', '*', 'eq.a', 'a%26user_id=neq.z',
                   'L1) or (user_id.neq.0', 'Bài ỏ ợ 😀', 'a' * 5000, 'L1\r\nX-Injected: 1']


@pytest.fixture
def upstream(monkeypatch):
    """Kho Supabase giả: ghi lại mọi truy vấn, luôn trả danh sách rỗng."""
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[])
    repo = supabase_repo_override(handler)
    app.dependency_overrides[require_coach] = lambda: COACH_A
    app.dependency_overrides[get_run_repository] = lambda: repo
    yield TestClient(app), calls
    app.dependency_overrides.clear()


def _query(request):
    return parse_qsl(request.url.query.decode(), keep_blank_values=True)


def _assert_owner_scoped(calls):
    for call in calls:
        keys = [k for k, _ in _query(call)]
        assert keys.count('user_id') == 1 or call.url.path.endswith('/rpc/review_recommendation')
        if keys.count('user_id'):
            assert dict(_query(call))['user_id'] == f"eq.{COACH_A['id']}"
        assert '*' not in dict(_query(call)).get('select', '')


@pytest.mark.parametrize('payload', LESSON_PAYLOADS)
def test_list_lesson_id_is_a_value_not_a_filter(upstream, payload):
    client, calls = upstream
    res = client.get('/api/analysis-runs', params={'lesson_id': payload})
    if len(payload) > 1000:  # giới hạn độ dài là hợp lệ, miễn là bị chặn trước khi chạm DB
        assert res.status_code in (400, 422) and calls == []
        return
    assert res.status_code == 200 and res.json()['items'] == []
    [call] = calls
    query = _query(call)
    assert dict(query)['lesson_id'] == f'eq.{payload}'  # nguyên văn như một giá trị, không tách thành tham số mới
    allowed = {'select', 'user_id', 'order', 'limit', 'lesson_id'}
    assert {k for k, _ in query} == allowed
    _assert_owner_scoped(calls)


@pytest.mark.parametrize('param,value', [
    ('status', "draft' or '1'='1"), ('status', 'draft&user_id=neq.x'), ('status', 'DRAFT'), ('status', ''),
    ('ai_status', 'not_enabled,user_id.neq.0'), ('ai_status', 'is.null'), ('ai_status', 'NOT_ENABLED')])
def test_list_status_and_ai_status_are_whitelisted(upstream, param, value):
    client, calls = upstream
    res = client.get('/api/analysis-runs', params={param: value})
    assert res.status_code == 422
    assert not any(value and value in call.url.query.decode() for call in calls)  # không đẩy giá trị lạ lên DB


def _cursor(created_at, run_id):
    raw = json.dumps({'c': created_at, 'i': run_id}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


def _expected_or(created_at, run_id):
    def quote(v):
        return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return (f'(created_at.lt.{quote(created_at)},and(created_at.eq.{quote(created_at)},id.lt.{quote(run_id)}))')


CURSORS = {
    'break_out_quote': _cursor('2026-11-27T10:00:00+00:00"),user_id.neq.x,and(id.eq."', RUN_UUID),
    'break_out_id': _cursor('2026-11-27T10:00:00+00:00', 'x"),user_id.neq.0,and(id.eq."'),
    'backslashes': _cursor('2026\\"\\', '\\\\"'),
    'sql_like': _cursor("'; drop table analysis_runs;--", "' or 1=1--"),
    'long': _cursor('2' * 10_000, RUN_UUID),
    'not_json': base64.urlsafe_b64encode(b'not json').decode(),
    'wrong_types': base64.urlsafe_b64encode(json.dumps({'c': 1, 'i': ['x']}).encode()).decode(),
    'null_values': base64.urlsafe_b64encode(json.dumps({'c': None, 'i': None}).encode()).decode(),
    'extra_keys': base64.urlsafe_b64encode(json.dumps({'c': 'x', 'i': 'y', 'user_id': COACH_B['id']}).encode()).decode(),
    'junk': '%00%00',
}


@pytest.mark.parametrize('name', sorted(CURSORS))
def test_cursor_is_validated_or_safely_quoted(upstream, name):
    client, calls = upstream
    res = client.get('/api/analysis-runs', params={'cursor': CURSORS[name]})
    assert res.status_code in (200, 400, 422)  # không bao giờ 500; 422 = giới hạn độ dài
    _assert_owner_scoped(calls)
    for call in calls:
        query = dict(_query(call))
        if 'or' in query and res.status_code == 200:
            decoded = json.loads(base64.urlsafe_b64decode(CURSORS[name] + '=' * (-len(CURSORS[name]) % 4)))
            assert query['or'] == _expected_or(decoded['c'], decoded['i'])


@pytest.mark.parametrize('run_id', ['x&user_id=neq.1', f'{RUN_UUID}&select=*', f'{RUN_UUID}?user_id=neq.0', "x' or '1'='1",
                                    '%00', 'null', 'eq.1,or(id.neq.0)'])
def test_non_uuid_run_id_is_404_without_touching_the_database(upstream, run_id):
    client, calls = upstream
    run_id = quote(run_id, safe='')  # '?' và '&' đi vào tham số đường dẫn, không thành query string
    assert client.get(f'/api/analysis-runs/{run_id}').status_code == 404
    assert client.get(f'/api/analysis-runs/{run_id}/export').status_code == 404
    assert copilot(client, run_id, 'compare_previous').status_code == 404
    assert review(client, run_id, RUN_UUID, 1, 'accept').status_code == 404
    assert calls == []


def test_non_uuid_recommendation_id_is_404_without_rpc(upstream):
    client, calls = upstream
    for rec_id in ('x', f'{RUN_UUID}&p_actor_id=eq.other', "'; drop table recommendations;--"):
        res = review(client, RUN_UUID, rec_id, 1, 'accept')
        assert res.status_code == 404
    assert not any(c.url.path.endswith('/rpc/review_recommendation') for c in calls)


@pytest.mark.parametrize('payload', ['version', 'generated_at', 'min_sample', 'catalog', 'lessons', '__class__', "L1' or 1=1",
                                     '../../etc/passwd', '<script>alert(1)</script>', 'L1\x00'])
def test_lesson_id_is_looked_up_only_among_catalog_lessons(rg_coach, rg_snap, rg_repo, payload):
    c = rg_coach(COACH_A)
    dash = c.get('/api/dashboard', params={'lesson_id': payload})
    assert dash.status_code == 404 and payload not in dash.text
    created = c.post('/api/analysis-runs', json={'lesson_id': payload, 'request_id': 'inj'})
    assert created.status_code in (404, 422) and rg_repo.runs == {}


@pytest.mark.parametrize('kc', ['__class__', 'priority', 'kcs', 'K1 ', 'k1', "K1' or '1'='1", 'K1\x00', 'K' * 5000])
def test_copilot_kc_code_must_be_exact_member_of_stored_snapshot(rg_coach, rg_snap, kc):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    for action in ('explain_priority', 'compare_previous'):
        res = copilot(c, run_id, action, kc)
        detail = res.json()['detail']
        assert res.status_code == 422 and (isinstance(detail, list) or detail['code'] == 'kc_not_in_snapshot')
        assert 'evidence' not in res.json()


# --- Khoá service role không lộ ra ngoài (mục f) ---

@pytest.fixture
def server_env(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', SERVICE_KEY)
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public-key-ok-to-expose')
    app.dependency_overrides[require_coach] = lambda: COACH_A
    yield monkeypatch
    app.dependency_overrides.clear()


def _failing_transport(monkeypatch, behaviour):
    """Mọi httpx.Client của backend trỏ vào `behaviour(request)`; kẻ tấn công điều khiển nội dung lỗi."""
    real = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kw: real(transport=httpx.MockTransport(behaviour), **kw))


def _echo_500(request):
    return httpx.Response(500, text=f'internal {request.headers.get("apikey")} {request.headers.get("authorization")}')


def _echo_200_not_json(request):
    return httpx.Response(200, text=f'<html>{request.headers.get("apikey")}</html>')


def _echo_json_error(request):
    return httpx.Response(409, json={'code': 'XX', 'message': request.headers.get('apikey'),
                                     'details': request.headers.get('authorization')})


def _connect_error(request):
    raise httpx.ConnectError(f'cannot connect with {request.headers.get("apikey")} to {request.url}', request=request)


def _timeout(request):
    raise httpx.ReadTimeout(f'Authorization: {request.headers.get("authorization")}', request=request)


ENDPOINTS = [
    ('GET', f'/api/analysis-runs', None),
    ('POST', '/api/analysis-runs', {'lesson_id': 'L1', 'request_id': 'r1'}),
    ('GET', f'/api/analysis-runs/{RUN_UUID}', None),
    ('GET', f'/api/analysis-runs/{RUN_UUID}/export', None),
    ('POST', f'/api/analysis-runs/{RUN_UUID}/reviews',
     {'recommendation_id': RUN_UUID, 'version': 1, 'decision': 'accept'}),
    ('POST', f'/api/analysis-runs/{RUN_UUID}/copilot', {'action': 'compare_previous'}),
]


@pytest.mark.parametrize('behaviour', [_echo_500, _echo_200_not_json, _echo_json_error, _connect_error, _timeout],
                         ids=lambda f: f.__name__)
@pytest.mark.parametrize('method,path,body', ENDPOINTS, ids=lambda v: v if isinstance(v, str) else None)
def test_service_key_absent_from_responses_and_logs_when_database_fails(server_env, rg_snap, caplog, behaviour, method,
                                                                         path, body):
    _failing_transport(server_env, behaviour)
    caplog.set_level(logging.DEBUG)
    client = TestClient(app, raise_server_exceptions=False)
    res = client.request(method, path, json=body)
    assert res.status_code in (404, 409, 422, 500, 503)
    leaked = [res.text, json.dumps(dict(res.headers)), caplog.text, *[repr(r.__dict__) for r in caplog.records]]
    assert all(SERVICE_KEY not in chunk for chunk in leaked)
    assert res.status_code != 500  # lỗi hạ tầng phải được map sang 503 ổn định, không rò stack trace


def test_public_config_exposes_only_publishable_values(server_env):
    res = TestClient(app).get('/api/config')
    assert set(res.json()) == {'supabase_url', 'supabase_publishable_key'}
    assert SERVICE_KEY not in res.text and 'service' not in res.text.lower()
    assert SERVICE_KEY not in TestClient(app).get('/openapi.json').text


def test_service_key_missing_gives_503_without_naming_the_secret(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    app.dependency_overrides[require_coach] = lambda: COACH_A
    try:
        for method, path, body in ENDPOINTS:
            res = TestClient(app).request(method, path, json=body)
            assert res.status_code == 503
            assert 'SERVICE_ROLE' not in res.text.upper().replace(' ', '_')
    finally:
        app.dependency_overrides.clear()


def test_frontend_bundle_and_sources_never_reference_service_role():
    roots = [ROOT / 'codebase/frontend/src', ROOT / 'codebase/frontend/dist']
    scanned = 0
    for root in roots:
        for path in root.rglob('*') if root.is_dir() else []:
            if path.is_file() and path.suffix in {'.ts', '.tsx', '.js', '.css', '.html', '.json', '.map'}:
                text = path.read_text(encoding='utf-8', errors='ignore')
                scanned += 1
                assert 'service_role' not in text.lower().replace('-', '_') and 'SERVICE_ROLE' not in text, path
    assert scanned > 0
