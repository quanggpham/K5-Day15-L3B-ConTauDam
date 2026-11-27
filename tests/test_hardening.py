import json

import pytest
from fastapi.testclient import TestClient

from codebase.backend.main import app
from codebase.backend.security import rate_limit
from codebase.backend.security.headers import content_security_policy
from tests.test_analysis_runs import COACH_A, COACH_B, as_coach, repo, snap_path  # noqa: F401


def test_security_headers_on_api_and_spa_routes(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://abc.supabase.co')
    client = TestClient(app)
    for path in ('/api/health', '/does-not-exist'):
        res = client.get(path)
        assert res.headers['X-Content-Type-Options'] == 'nosniff'
        assert res.headers['X-Frame-Options'] == 'DENY'
        assert res.headers['Referrer-Policy'] == 'no-referrer'
        assert "frame-ancestors 'none'" in res.headers['Content-Security-Policy']


def test_csp_blocks_inline_scripts_and_allows_only_own_and_supabase_connections(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://abc.supabase.co/')
    csp = content_security_policy()
    assert "script-src 'self'" in csp and 'unsafe-eval' not in csp and "script-src 'self' 'unsafe-inline'" not in csp
    assert "connect-src 'self' https://abc.supabase.co wss://abc.supabase.co" in csp
    assert "object-src 'none'" in csp and "base-uri 'self'" in csp


@pytest.mark.parametrize('bad', ['', 'javascript:alert(1)', 'not a url'])
def test_csp_ignores_missing_or_malformed_supabase_url(monkeypatch, bad):
    monkeypatch.setenv('SUPABASE_URL', bad)
    assert "connect-src 'self'" in content_security_policy()
    assert 'javascript' not in content_security_policy()


def test_create_run_rate_limited_per_coach_with_retry_after(as_coach, snap_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv('RUN_CREATE_LIMIT_PER_MIN', '3')
    client = as_coach(COACH_A)
    for i in range(3):
        assert client.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': f'r{i}'}).status_code == 201
    res = client.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'r3'})
    assert res.status_code == 429 and int(res.headers['Retry-After']) >= 1
    # retry của request đã tạo (idempotent) không bị tính và không bị chặn
    assert client.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'r0'}).status_code == 200
    # coach khác có hạn mức riêng
    other = as_coach(COACH_B)
    assert other.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'b0'}).status_code == 201


def test_rate_limit_window_slides():
    assert rate_limit.try_acquire('u', now=0.0) is None
    for _ in range(rate_limit.creates_per_window() - 1):
        assert rate_limit.try_acquire('u', now=1.0) is None
    wait = rate_limit.try_acquire('u', now=2.0)
    assert wait is not None and wait > 0
    assert rate_limit.try_acquire('u', now=rate_limit.WINDOW_SECONDS + 1.5) is None  # lượt cũ đã trôi ra khỏi cửa sổ
