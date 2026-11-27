"""Test cho các việc nhỏ sau review: replay chặt, allowlist SQL, hạn mức hoàn lượt/dọn khoá, cursor lạ, header cho 500."""
import base64
import json
import re

import pytest
from fastapi.testclient import TestClient

from codebase.backend.analytics.workflow import create_report
from codebase.backend.api.run_repository import RECOMMENDATION_FIELDS, REVIEW_FIELDS, RepositoryError
from codebase.backend.main import app
from codebase.backend.security import rate_limit
from tests.test_analysis_runs import COACH_A
from tests.test_reviews_copilot import MIGRATION, _review, as_coach, repo, run_rec, snap_path  # noqa: F401


def test_retry_of_an_overwritten_decision_is_a_conflict_not_a_replay(as_coach, run_rec, repo):  # noqa: F811
    """v1 accept -> v2, reject@2 -> v3, rồi gửi lại accept@1: không được trả 'replayed' (đề xuất đang 'rejected')."""
    run_id, rec = run_rec
    c = as_coach(COACH_A)
    assert _review(c, run_id, rec['id'], 1, 'accept').status_code == 201
    assert _review(c, run_id, rec['id'], 2, 'reject').status_code == 201
    stale = _review(c, run_id, rec['id'], 1, 'accept')
    assert stale.status_code == 409 and stale.json()['detail']['code'] == 'version_conflict'
    assert stale.json()['detail']['recommendation']['review_status'] == 'rejected'
    assert len(repo.reviews) == 2


def _sql_keys(variable: str) -> set[str]:
    sql = MIGRATION.read_text(encoding='utf-8')
    block = re.search(rf'{variable}\s*:=\s*jsonb_build_object\((.*?)\);', sql, re.DOTALL).group(1)
    return set(re.findall(r"'(\w+)',\s*v_\w+\.", block))


def test_sql_jsonb_allowlist_matches_python_field_tuples():
    """Khoá trong hàm SQL phải trùng RECOMMENDATION_FIELDS / REVIEW_FIELDS: cột mới không tự lộ, cột bỏ không hỏng."""
    assert _sql_keys('v_rec_json') == set(RECOMMENDATION_FIELDS)
    assert _sql_keys('v_review_json') == set(REVIEW_FIELDS)
    assert 'actor_email' not in _sql_keys('v_review_json')


def test_v1_report_does_not_rank_a_zero_error_kc():
    snapshot = {'L1': [
        {'kc_code': 'A', 'incorrect_rate': 0.0, 'graded_count': 20},
        {'kc_code': 'B', 'incorrect_rate': 0.3, 'graded_count': 20},
        {'kc_code': 'C', 'incorrect_rate': None, 'graded_count': 0}]}
    ranked = create_report('L1', snapshot)['priority']
    assert [r['kc_code'] for r in ranked] == ['B']


def test_failed_insert_refunds_the_rate_limit_slot(as_coach, snap_path, repo, monkeypatch):  # noqa: F811
    monkeypatch.setenv('RUN_CREATE_LIMIT_PER_MIN', '1')
    client = as_coach(COACH_A)
    real_insert = repo.insert_run

    def broken(*args, **kwargs):
        raise RepositoryError('db down')
    monkeypatch.setattr(repo, 'insert_run', broken)
    assert client.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'x1'}).status_code == 503
    monkeypatch.setattr(repo, 'insert_run', real_insert)
    # lần lỗi không tốn lượt: lần tạo thật sự đầu tiên vẫn được phép dù hạn mức chỉ là 1
    assert client.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'x2'}).status_code == 201
    assert client.post('/api/analysis-runs', json={'lesson_id': 'L2', 'request_id': 'x3'}).status_code == 429


def test_rate_limiter_sweeps_expired_keys_and_refund_is_safe():
    for i in range(rate_limit.SWEEP_ABOVE_KEYS + 5):
        assert rate_limit.try_acquire(f'user-{i}', now=0.0) is None
    assert len(rate_limit._hits) > rate_limit.SWEEP_ABOVE_KEYS
    assert rate_limit.try_acquire('late', now=rate_limit.WINDOW_SECONDS + 5) is None
    assert set(rate_limit._hits) == {'late'}  # khoá hết hạn đã bị dọn
    rate_limit.refund('nobody')  # không lỗi khi chưa có lượt
    rate_limit.refund('late')
    assert rate_limit.try_acquire('late', now=rate_limit.WINDOW_SECONDS + 6) is None


@pytest.mark.parametrize('stamp', ['2026-W48-5T10:00:00+00:00', '2026-11-27', '20261127T100000+0000',
                                   '2026-11-27T10:00:00', '２０２６-11-27T10:00:00+00:00'])
def test_cursor_with_odd_iso_forms_is_422(as_coach, snap_path, stamp):  # noqa: F811
    raw = json.dumps({'c': stamp, 'i': '11111111-1111-1111-1111-111111111111'}).encode()
    cursor = base64.urlsafe_b64encode(raw).decode().rstrip('=')
    assert as_coach(COACH_A).get('/api/analysis-runs', params={'cursor': cursor}).status_code == 422


def test_unhandled_error_response_still_carries_security_headers():
    async def boom():
        raise RuntimeError('secret internal detail')
    app.add_api_route('/api/_boom_for_test', boom)
    route = app.router.routes.pop()
    app.router.routes.insert(0, route)  # đứng trước route bắt-tất-cả của SPA
    try:
        res = TestClient(app, raise_server_exceptions=False).get('/api/_boom_for_test')
    finally:
        app.router.routes.remove(route)
    assert res.status_code == 500 and 'secret internal detail' not in res.text
    assert res.headers['X-Content-Type-Options'] == 'nosniff'
    assert "frame-ancestors 'none'" in res.headers['Content-Security-Policy']
