"""Fixtures và helper dùng chung cho các test hồi quy (quyền sở hữu, idempotency, CSV, duyệt, riêng tư).

Không phải module test (tên không khớp test_*.py). Dùng fake repo + auth giả như các test hiện có;
không đọc dữ liệu thật.
"""
import copy
import csv
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api.run_repository import InMemoryRunRepository, SupabaseRunRepository, get_run_repository
from codebase.backend.main import app
from codebase.backend.security.auth import require_coach
from tests.test_analysis_runs import COACH_A, COACH_B, Clock
from tests.test_reviews_copilot import _lesson_snapshot

MISSING_UUID = '00000000-0000-0000-0000-000000000000'
NOT_RECORDED = 'chưa được ghi nhận'
SERVICE_KEY = 'srv-role-KEY-9f8e7d6c5b4a'


@pytest.fixture
def rg_repo():
    return InMemoryRunRepository(clock=Clock())


@pytest.fixture
def rg_snap(tmp_path, monkeypatch):
    path = tmp_path / 'agg.v2.json'
    path.write_text(json.dumps(_lesson_snapshot()), encoding='utf-8')
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


@pytest.fixture
def rg_coach(rg_repo):
    """Trả `switch(user) -> TestClient`; mọi request sau đó chạy với người dùng đó."""
    current = {'user': COACH_A}
    app.dependency_overrides[require_coach] = lambda: current['user']
    app.dependency_overrides[get_run_repository] = lambda: rg_repo

    def switch(user=COACH_A, **client_kwargs):
        current['user'] = user
        return TestClient(app, **client_kwargs)
    yield switch
    app.dependency_overrides.clear()


def create_run(client, lesson='L2', request_id='req-1'):
    res = client.post('/api/analysis-runs', json={'lesson_id': lesson, 'request_id': request_id})
    assert res.status_code in (200, 201), res.text
    return res.json()['run_id']


def review(client, run_id, rec_id, version, decision, **extra):
    return client.post(f'/api/analysis-runs/{run_id}/reviews',
                       json={'recommendation_id': rec_id, 'version': version, 'decision': decision, **extra})


def copilot(client, run_id, action, kc_code=None):
    body = {'action': action, **({'kc_code': kc_code} if kc_code is not None else {})}
    return client.post(f'/api/analysis-runs/{run_id}/copilot', json=body)


def csv_rows(response):
    assert response.status_code == 200, response.text
    return list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'), newline='')))


def state_of(repo):
    """Ảnh chụp toàn bộ trạng thái kho để so sánh 'không có tác dụng phụ'."""
    return copy.deepcopy((repo.runs, repo.recommendations, repo.evaluations, repo.reviews))


def supabase_repo_override(handler, key=SERVICE_KEY):
    """SupabaseRunRepository thật nhưng đi qua MockTransport (không mạng)."""
    client_type = httpx.Client
    return SupabaseRunRepository(
        'https://example.test', key,
        client_factory=lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
