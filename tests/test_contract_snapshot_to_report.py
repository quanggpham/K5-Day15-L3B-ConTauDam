"""Hợp đồng producer→consumer: build_snapshot THẬT → tạo run → báo cáo đã lưu → những gì frontend cần.

Lỗi từng lọt qua vì fixture viết tay: run lưu thiếu `distribution`... nên tab Tổng quan trống và Copilot bị khoá.
Ở đây dữ liệu đi qua đúng đường sản phẩm: DuckDB → build_snapshot → file v2 → POST /api/analysis-runs → GET detail.
"""
import json

import pytest

from codebase.backend.analytics.metrics import build_snapshot
from codebase.backend.api.lesson_view import LESSON_VIEW_KEYS
from tests.test_analysis_runs import COACH_A, as_coach, repo  # noqa: F401  (fixtures dùng chung)
from tests.test_snapshot_v2 import make_db


def _rows():
    rows = []
    for i in range(12):  # L1: K1 sai 3/12, K2 sai 6/12 (đủ mẫu, có xếp ưu tiên)
        rows.append(('L1', 'K1', 1, i >= 3, f'a{i}'))
        rows.append(('L1', 'K2', 1, i >= 6, f'a{i}'))
    for i in range(12):  # L2: K1 sai 6/12, K2 chưa chấm, K3 chỉ 4 lượt (chưa đủ mẫu)
        rows.append(('L2', 'K1', 1, i >= 6, f'b{i}'))
        rows.append(('L2', 'K2', 1, None, f'b{i}'))
    rows += [('L2', 'K3', 1, False, f'c{i}') for i in range(4)]
    return rows


@pytest.fixture
def real_snapshot_path(tmp_path, monkeypatch):
    path = tmp_path / 'aggregate.v2.json'
    path.write_text(json.dumps(build_snapshot(make_db(_rows()), generated_at='2026-11-27T00:00:00+00:00')))
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


def _create(client, lesson_id, request_id):
    res = client.post('/api/analysis-runs', json={'lesson_id': lesson_id, 'request_id': request_id})
    assert res.status_code in (200, 201), res.text
    return res.json()


def _run_id(created):
    return created['run_id']


def test_stored_report_has_every_key_the_frontend_requires(as_coach, real_snapshot_path):
    client = as_coach(COACH_A)
    run_id = _run_id(_create(client, 'L2', 'contract-1'))
    detail = client.get(f'/api/analysis-runs/{run_id}').json()
    stored = detail['snapshot']
    assert stored['format'] == 'analysis_run_snapshot/1' and stored.get('notice') is None
    lesson = stored['data']['lesson']
    # frontend/src/features/reports/snapshot.ts isLessonView
    assert isinstance(lesson['sample'], dict) and isinstance(lesson['distribution'], dict)
    assert isinstance(lesson['kcs'], list) and isinstance(lesson['priority'], list)
    assert set(LESSON_VIEW_KEYS) <= set(lesson)


def test_stored_numbers_match_what_build_snapshot_computed(as_coach, real_snapshot_path):
    client = as_coach(COACH_A)
    expected = build_snapshot(make_db(_rows()))['lessons']['L2']
    run_id = _run_id(_create(client, 'L2', 'contract-2'))
    lesson = client.get(f'/api/analysis-runs/{run_id}').json()['snapshot']['data']['lesson']
    assert lesson['sample']['responses'] == expected['sample']['responses']
    dist = lesson['distribution']
    assert dist['correct'] + dist['incorrect'] == lesson['sample']['responses']
    assert dist['ungraded'] == expected['sample']['ungraded']
    assert lesson['previous_lesson_id'] == 'L1'
    # K2 chưa chấm → không có tỷ lệ, không bị biến thành 0%; K3 dưới 10 lượt → không xếp hạng
    by_kc = {k['kc_code']: k for k in lesson['kcs']}
    assert by_kc['K2']['status'] == 'no_graded' and by_kc['K2']['incorrect_rate'] is None
    assert by_kc['K3']['status'] == 'insufficient_sample'
    assert 'K3' not in {p['kc_code'] for p in lesson['priority']}


def test_dashboard_and_stored_report_share_one_lesson_view(as_coach, real_snapshot_path):
    client = as_coach(COACH_A)
    dash = client.get('/api/dashboard', params={'lesson_id': 'L2'}).json()['lesson']
    run_id = _run_id(_create(client, 'L2', 'contract-3'))
    stored = client.get(f'/api/analysis-runs/{run_id}').json()['snapshot']['data']['lesson']
    assert stored == dash


def test_copilot_and_export_work_on_a_freshly_created_run(as_coach, real_snapshot_path):
    client = as_coach(COACH_A)
    run_id = _run_id(_create(client, 'L2', 'contract-4'))
    res = client.post(f'/api/analysis-runs/{run_id}/copilot', json={'action': 'explain_priority', 'kc_code': 'K1'})
    assert res.status_code == 200 and res.json()['source'] == 'stored_snapshot'
    res = client.post(f'/api/analysis-runs/{run_id}/copilot', json={'action': 'compare_previous'})
    assert res.status_code == 200
    export = client.get(f'/api/analysis-runs/{run_id}/export')
    assert export.status_code == 200 and 'K1' in export.content.decode('utf-8-sig')


def test_legacy_stored_lesson_without_view_keys_is_normalized_on_read(as_coach, repo, real_snapshot_path):  # noqa: F811
    """Run tạo bởi bản cũ lưu nguyên bài của build_snapshot (không distribution) vẫn đọc được, không điền 0."""
    raw = build_snapshot(make_db(_rows()))['lessons']['L1']
    run = repo.seed_run(COACH_A['id'], lesson_id='L1', status='draft', metrics_snapshot={
        'schema': 'analysis_run_snapshot/1', 'snapshot_version': 'v2', 'lesson': raw})
    lesson = as_coach(COACH_A).get(f"/api/analysis-runs/{run['id']}").json()['snapshot']['data']['lesson']
    assert isinstance(lesson['distribution'], dict) and set(LESSON_VIEW_KEYS) <= set(lesson)
