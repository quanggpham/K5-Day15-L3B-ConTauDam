"""KC nhóm nhỏ (<5 người) đi qua toàn bộ đường API: dashboard, báo cáo đã lưu, CSV, Copilot không lộ số liệu."""
import json

import pytest

from codebase.backend.analytics.metrics import build_snapshot
from tests.test_analysis_runs import COACH_A, as_coach, repo  # noqa: F401
from tests.test_snapshot_v2 import make_db


def _rows():
    rows = [('L1', 'SMALL', 1, i % 2 == 0, f'S{n}') for n in range(3) for i in range(6)]  # 3 người, 18 lượt
    rows += [('L1', 'BIG', 1, i >= 3, f'B{i}') for i in range(12)]                          # 12 người
    return rows


@pytest.fixture
def snap_file(tmp_path, monkeypatch):
    path = tmp_path / 'aggregate.v2.json'
    path.write_text(json.dumps(build_snapshot(make_db(_rows()), generated_at='2026-11-27T00:00:00+00:00')))
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    return path


def _run(client):
    return client.post('/api/analysis-runs', json={'lesson_id': 'L1', 'request_id': 'sg-1'}).json()['run_id']


def test_dashboard_and_stored_report_hide_the_small_group(as_coach, snap_file):
    client = as_coach(COACH_A)
    dash = client.get('/api/dashboard', params={'lesson_id': 'L1'}).json()['lesson']
    small = next(k for k in dash['kcs'] if k['kc_code'] == 'SMALL')
    assert small['status'] == 'small_group' and small['graded_count'] is None and small['incorrect_rate'] is None
    assert dash['sample']['responses'] == 12 and dash['sample']['masked_kc_count'] == 1
    assert [p['kc_code'] for p in dash['priority']] == ['BIG']
    stored = client.get(f'/api/analysis-runs/{_run(client)}').json()['snapshot']['data']['lesson']
    assert stored == dash


def test_csv_marks_hidden_numbers_instead_of_exporting_or_calling_them_unrecorded(as_coach, snap_file):
    client = as_coach(COACH_A)
    text = client.get(f'/api/analysis-runs/{_run(client)}/export').content.decode('utf-8-sig')
    row = next(line for line in text.splitlines() if 'SMALL' in line)
    assert 'ẩn: mẫu nhỏ' in row and 'small_group' in row and '18' not in row.split('small_group')[1]
    assert 'chưa được ghi nhận' not in row


def test_copilot_explains_without_revealing_numbers(as_coach, snap_file):
    client = as_coach(COACH_A)
    res = client.post(f'/api/analysis-runs/{_run(client)}/copilot', json={'action': 'explain_priority', 'kc_code': 'SMALL'})
    body = res.json()
    assert res.status_code == 200 and 'ẩn' in body['message'] and 'dưới 5' in body['message']
    assert '18' not in body['message']
    for item in body['evidence']:
        assert item['field'] in ('kcs.status', 'min_sample') and item['value'] != 18
