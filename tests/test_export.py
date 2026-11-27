import copy
import csv
import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api.export import HEADER, _safe_text
from codebase.backend.api.run_repository import InMemoryRunRepository, RepositoryError, get_run_repository
from codebase.backend.main import app
from codebase.backend.security import auth
from codebase.backend.security.auth import require_coach
from tests.test_analysis_runs import COACH_A, COACH_B, Clock, _post, snap_path  # noqa: F401
from tests.test_dashboard import SNAP

NOT_RECORDED = 'chưa được ghi nhận'


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


def _rows(response):
    assert response.content.startswith('﻿'.encode('utf-8'))  # BOM cho Excel
    return list(csv.reader(io.StringIO(response.content.decode('utf-8-sig'), newline='')))


def _export(client, run_id):
    return client.get(f'/api/analysis-runs/{run_id}/export')


def test_export_columns_values_and_headers(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    res = _export(c, run_id)
    assert res.status_code == 200
    assert res.headers['content-type'] == 'text/csv; charset=utf-8'
    assert res.headers['content-disposition'] == f'attachment; filename="learningpulse-L1-{run_id[:8]}.csv"'
    assert res.headers['cache-control'] == 'no-store'
    rows = _rows(res)
    assert rows[0] == HEADER and all(len(r) == len(HEADER) for r in rows)
    by_kind = {(r[0], r[2]): r for r in rows[1:]}
    report = by_kind[('Báo cáo', '')]
    assert report[1] == 'L1' and report[3] == 'draft' and report[4] == '20' and report[5] == '15'
    assert report[6] == '0.5' and 'snapshot_version=v2:t' in report[12] and 'ngưỡng mẫu tối thiểu (lượt)=10' in report[12]
    k1, k2 = by_kind[('Số liệu KC', 'K1')], by_kind[('Số liệu KC', 'K2')]
    assert (k1[3], k1[4], k1[6], k1[7]) == ('ok', '20', '0.5', '1')
    assert (k2[3], k2[4], k2[6], k2[7]) == ('insufficient_sample', '3', '1.0', '')
    assert k1[5] == NOT_RECORDED  # snapshot không có số người theo KC: không in 0
    assert 'Tỷ lệ sai' in HEADER[6] and 'lượt' in HEADER[4] and 'người' in HEADER[5]


def test_export_uses_stored_snapshot_not_current(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    changed = copy.deepcopy(SNAP)
    changed['lessons']['L1']['sample']['responses'] = 999
    changed['lessons']['L1']['incorrect_rate'] = 0.99
    snap_path.write_text(json.dumps(changed), encoding='utf-8')
    report = _rows(_export(c, run_id))[1]
    assert report[4] == '20' and report[6] == '0.5'


def test_kc_learner_count_from_snapshot_v2_is_exported(as_coach, repo):
    snap = {'schema': 'analysis_run_snapshot/1', 'snapshot_version': 'v2', 'lesson': {
        'lesson_id': 'L7', 'status': 'ok', 'sample': {'responses': 12, 'learners': 9, 'ungraded': 0},
        'incorrect_rate': 0.25, 'kcs': [{'kc_code': 'K7', 'status': 'ok', 'graded_count': 12,
                                         'learner_count': 7, 'incorrect_rate': 0.25}]}}
    run = repo.seed_run(COACH_A['id'], lesson_id='L7', metrics_snapshot=snap, status='draft')
    kc = _rows(_export(as_coach(COACH_A), run['id']))[2]
    assert (kc[4], kc[5]) == ('12', '7')


def test_no_graded_and_zero_are_distinct_from_missing(as_coach, repo):
    snap = {'schema': 'analysis_run_snapshot/1', 'snapshot_version': 'v2', 'lesson': {
        'lesson_id': 'L9', 'status': 'no_graded', 'sample': {'responses': 0, 'learners': 0, 'ungraded': 5},
        'incorrect_rate': None, 'kcs': [{'kc_code': 'K9', 'status': 'no_graded', 'graded_count': 0,
                                         'incorrect_rate': None}]}}
    run = repo.seed_run(COACH_A['id'], lesson_id='L9', metrics_snapshot=snap, status='draft')
    rows = _rows(_export(as_coach(COACH_A), run['id']))
    report, kc = rows[1], rows[2]
    assert (report[4], report[5], report[6]) == ('0', '0', 'không có lượt chấm')
    assert (kc[3], kc[4], kc[6]) == ('no_graded', '0', 'không có lượt chấm')


def test_recommendations_sources_and_review_status(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    repo.recommendations += [
        {'id': 'r1', 'analysis_run_id': run_id, 'kc_code': 'K1', 'priority': 1, 'content': 'Ôn lại phần Tiếng Việt',
         'citations': [{'source_id': 'KB-1', 'title': 'Bài giảng 1'}], 'review_status': 'accepted',
         'is_edited': True, 'needs_rereview': False, 'version': 2},
        {'id': 'r2', 'analysis_run_id': run_id, 'kc_code': 'K2', 'priority': 2, 'content': 'x', 'citations': [],
         'review_status': None}]
    repo.reviews.append({'id': 'v1', 'run_id': run_id, 'recommendation_id': 'r1', 'at': '2026-11-27T11:00:00Z',
                         'decision': 'accept', 'comment': 'Được', 'content_after': None, 'new_version': 2})
    rows = _rows(_export(c, run_id))
    rec1 = next(r for r in rows if r[0] == 'Đề xuất' and r[2] == 'K1')
    rec2 = next(r for r in rows if r[0] == 'Đề xuất' and r[2] == 'K2')
    assert rec1[8] == 'Ôn lại phần Tiếng Việt' and rec1[9] == 'KB-1 · Bài giảng 1' and rec1[10] == 'accepted'
    assert rec2[9] == '' and rec2[10] == NOT_RECORDED  # không bịa nguồn; trạng thái duyệt chưa ghi nhận
    review = next(r for r in rows if r[0] == 'Lịch sử duyệt')
    assert review[2] == 'K1' and review[10] == 'accept' and review[11] == 'Được'


PAYLOADS = ['=cmd|"/c calc"!A0', '+1+1', '-2', '@SUM(A1)', '\tx', '\rx', ' =x', '  \t+1', '\n=1']


@pytest.mark.parametrize('payload', PAYLOADS)
def test_formula_payloads_neutralized_everywhere(as_coach, snap_path, repo, payload):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    repo.runs[run_id]['metrics_snapshot']['lesson']['kcs'][0]['kc_code'] = payload
    repo.recommendations.append({'id': 'r1', 'analysis_run_id': run_id, 'kc_code': payload, 'priority': 1,
                                 'content': payload, 'citations': [payload], 'review_status': payload})
    repo.reviews.append({'id': 'v1', 'run_id': run_id, 'recommendation_id': 'r1', 'at': '2026-11-27T11:00:00Z',
                         'decision': payload, 'comment': payload, 'content_after': payload})
    rows = _rows(_export(c, run_id))
    checked = 0
    for row in rows[1:]:
        for cell in row:
            if cell.lstrip("'") == payload:
                assert cell == "'" + payload
                checked += 1
    assert checked >= 8  # kc ở số liệu + đề xuất + duyệt; content, citations, review, comment, decision...
    for row in rows[1:]:
        for cell in row:
            assert cell[:1] not in ('=', '+', '-', '@', '\t', '\r')
            assert cell.lstrip()[:1] not in ('=', '+', '-', '@')


def test_valid_numbers_not_broken(as_coach, snap_path, repo):
    run_id = _post(as_coach(COACH_A)).json()['run_id']
    repo.runs[run_id]['metrics_snapshot']['lesson']['incorrect_rate'] = -0.5  # số âm hợp lệ là số, không phải văn bản
    rows = _rows(_export(as_coach(COACH_A), run_id))
    assert rows[1][6] == '-0.5'
    assert _safe_text('-2') == "'-2" and _safe_text('abc-1') == 'abc-1' and _safe_text(None) == ''


def test_csv_quoting_unicode_and_multiline(as_coach, snap_path, repo):
    c = as_coach(COACH_A)
    run_id = _post(c).json()['run_id']
    tricky = 'Học viên "A", nhầm\nphần Đạo hàm — ư ơ ê ạ, 😀'
    repo.recommendations.append({'id': 'r1', 'analysis_run_id': run_id, 'kc_code': 'K,1', 'priority': 1,
                                 'content': tricky, 'citations': [], 'review_status': 'pending'})
    res = _export(c, run_id)
    rec = next(r for r in _rows(res) if r[0] == 'Đề xuất')
    assert rec[8] == tricky and rec[2] == 'K,1'
    assert '"K,1"' in res.content.decode('utf-8-sig')


def test_filename_is_safe(as_coach, repo):
    run = repo.seed_run(COACH_A['id'], lesson_id='../a"b\r\nSet-Cookie: x', metrics_snapshot={})
    res = _export(as_coach(COACH_A), run['id'])
    disposition = res.headers['content-disposition']
    assert res.status_code == 200 and disposition.startswith('attachment; filename="learningpulse-')
    name = disposition.split('filename="')[1].rstrip('"')
    assert all(ch.isalnum() or ch in '_-.' for ch in name) and '/' not in name


def test_legacy_draft_without_metadata_exports(as_coach, repo):
    legacy = repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot={})
    repo.recommendations.append({'id': 'r1', 'analysis_run_id': legacy['id'], 'kc_code': 'K1', 'priority': 1,
                                 'content': 'x', 'citations': []})  # thiếu review_status
    res = _export(as_coach(COACH_A), legacy['id'])
    rows = _rows(res)
    assert res.status_code == 200
    assert NOT_RECORDED in rows[1][12] and rows[1][4] == '' and rows[1][6] == ''  # không in 0
    assert 'snapshot_version=chưa được ghi nhận' in rows[1][12]
    assert rows[2][0] == 'Đề xuất' and rows[2][10] == NOT_RECORDED


def test_legacy_snapshot_format_not_reinterpreted(as_coach, repo):
    legacy = repo.seed_run(COACH_A['id'], metrics_snapshot={'L1': [{'kc_code': 'K1', 'incorrect_rate': 0.4}]})
    rows = _rows(_export(as_coach(COACH_A), legacy['id']))
    assert len(rows) == 2 and 'định dạng cũ' in rows[1][12] and '0.4' not in ''.join(rows[1])


def test_cross_owner_is_404_same_as_missing(as_coach, snap_path, repo):
    run_id = _post(as_coach(COACH_A)).json()['run_id']
    b = as_coach(COACH_B)
    other, missing = _export(b, run_id), _export(b, '00000000-0000-0000-0000-000000000000')
    assert other.status_code == missing.status_code == 404 and other.json() == missing.json()
    assert 'Content-Disposition' not in other.headers
    assert _export(as_coach(COACH_A), run_id).status_code == 200


def test_repository_failure_is_503(as_coach, repo):
    def boom(*a, **kw):
        raise RepositoryError('x')
    repo.get_run_detail = boom
    assert _export(as_coach(COACH_A), 'abc').status_code == 503


def test_export_requires_auth_401():
    assert TestClient(app).get('/api/analysis-runs/x/export').status_code == 401


def test_export_not_allowlisted_403(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public')

    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': COACH_A['id']})
        return httpx.Response(200, json=False)
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kw: client_type(transport=httpx.MockTransport(handler), **kw))
    assert TestClient(app).get('/api/analysis-runs/x/export', headers={'Authorization': 'Bearer x'}).status_code == 403
