"""Hồi quy CSV chống công thức, Copilot dùng snapshot đã lưu, không lộ mã học viên, nháp cũ (plan 001 step 10: c, e, g, h).

Spec: CSV "không để văn bản từ người dùng hoặc model bị bảng tính thực thi như công thức"; Copilot "chỉ đúng căn cứ trong
snapshot đã lưu", "điều kiện mở AI được kiểm tại server"; "không đưa mã học viên lên cloud"; "bản nháp cũ không có metadata
mới vẫn mở được".
"""
import json

import duckdb
import pytest

from codebase.backend.analytics.metrics import build_snapshot
from codebase.backend.api.export import HEADER
from tests.regression_support import (  # noqa: F401
    NOT_RECORDED, copilot, create_run, csv_rows, review, rg_coach, rg_repo, rg_snap, state_of)
from tests.test_analysis_runs import COACH_A

DANGEROUS_START = ('=', '+', '-', '@', '\t', '\r')
PAYLOADS = ['=cmd|"/c calc"!A0', '+1+1', '-2+3', '@SUM(A1)', '\tx', '\rx', ' =x', '  \t+1', '\n=1', '=HYPERLINK("http://e","x")']
WHITESPACE_VARIANTS = ['\x0b=1+1', '\x0c@x', '\xa0=1+1', ' +1', '　-1']  # lstrip() của Python coi là khoảng trắng


def _is_dangerous(cell: str) -> bool:
    return cell[:1] in DANGEROUS_START or cell.lstrip()[:1] in ('=', '+', '-', '@')


def _poisoned_run(repo, payload):
    """Run v2 hợp lệ mà MỌI chuỗi người dùng/model có thể điền (cả giá trị 'số' kiểu chuỗi) đều là payload."""
    snap = {'schema': 'analysis_run_snapshot/1', 'snapshot_version': 'v2', 'lesson': {
        'lesson_id': payload, 'status': payload, 'sample': {'responses': payload, 'learners': payload, 'ungraded': payload},
        'incorrect_rate': payload, 'delta_vs_previous_pp': payload,
        'kcs': [{'kc_code': payload, 'status': payload, 'graded_count': payload, 'learner_count': payload,
                 'incorrect_rate': payload, 'delta_vs_previous_pp': payload}]}}
    run = repo.seed_run(COACH_A['id'], lesson_id=payload, metrics_snapshot=snap, status=payload, ai_status=payload,
                        snapshot_version=payload)
    repo.recommendations.append({
        'id': 'r1', 'analysis_run_id': run['id'], 'kc_code': payload, 'priority': payload, 'content': payload,
        'citations': [payload, {'source_id': payload, 'title': payload, 'source': payload, 'url': payload}],
        'review_status': payload, 'version': 1})
    repo.reviews.append({
        'id': 'v1', 'run_id': run['id'], 'recommendation_id': 'r1', 'at': '2026-11-27T11:00:00Z', 'decision': payload,
        'comment': payload, 'content_before': payload, 'content_after': payload, 'actor_email': payload,
        'status_before': payload, 'status_after': payload, 'new_version': 2})
    return run['id']


@pytest.mark.parametrize('payload', PAYLOADS + WHITESPACE_VARIANTS)
def test_no_csv_cell_in_any_row_kind_can_start_a_formula(rg_coach, rg_repo, payload):
    c = rg_coach(COACH_A, raise_server_exceptions=False)
    run_id = _poisoned_run(rg_repo, payload)
    res = c.get(f'/api/analysis-runs/{run_id}/export')
    assert res.status_code == 200, res.text
    rows = csv_rows(res)
    kinds = {row[0] for row in rows[1:]}
    assert {'Báo cáo', 'Số liệu KC', 'Đề xuất', 'Lịch sử duyệt'} <= kinds
    assert all(len(row) == len(HEADER) for row in rows)
    for row in rows[1:]:
        for index, cell in enumerate(row):
            assert not _is_dangerous(cell), (row[0], HEADER[index], cell)
    # Vô hiệu hoá nhưng không làm mất nội dung: văn bản gốc vẫn đọc được ở các ô văn bản chính.
    visible = {cell.lstrip("'") for row in rows[1:] for cell in row}
    assert payload in visible


def test_numeric_looking_snapshot_strings_are_not_trusted_as_numbers(rg_coach, rg_repo):
    """Số liệu 'đã lưu' là chuỗi tuỳ ý (JSONB): '=1+1' không được lọt vào cột số."""
    run_id = _poisoned_run(rg_repo, '=1+1')
    rows = csv_rows(rg_coach(COACH_A).get(f'/api/analysis-runs/{run_id}/export'))
    for row in rows[1:3]:
        for column in (4, 5, 6, 7):
            assert row[column][:1] not in ('=', '+', '-', '@'), (row[0], HEADER[column], row[column])


def test_export_survives_unexpected_types_in_stored_fields(rg_coach, rg_repo):
    snap = {'schema': 'analysis_run_snapshot/1', 'snapshot_version': 'v2', 'lesson': {
        'lesson_id': 'L1', 'status': 'ok', 'sample': {'responses': True, 'learners': [1], 'ungraded': {'a': 1}},
        'incorrect_rate': {'x': 1}, 'kcs': [{'kc_code': 5, 'status': None, 'graded_count': None}, 'rác', None]}}
    run = rg_repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot=snap, status='draft')
    rg_repo.recommendations.append({'id': 'r1', 'analysis_run_id': run['id'], 'kc_code': None, 'priority': None,
                                    'content': None, 'citations': 'chuỗi thay vì danh sách', 'review_status': 5})
    res = rg_coach(COACH_A, raise_server_exceptions=False).get(f"/api/analysis-runs/{run['id']}/export")
    assert res.status_code == 200
    assert all(not _is_dangerous(cell) for row in csv_rows(res) for cell in row)


# --- (e) Copilot ---

@pytest.fixture
def no_model_no_network(monkeypatch):
    import importlib
    from pathlib import Path

    import httpx
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'codebase'))  # như test_liquid: ai.py import `tracing`
    ai = importlib.import_module('ai')

    def forbidden(*a, **kw):
        raise AssertionError('Copilot không được gọi model hoặc mạng')
    monkeypatch.setattr(ai, 'call_model', forbidden)
    monkeypatch.setattr(httpx, 'Client', forbidden)
    monkeypatch.setattr(httpx, 'AsyncClient', forbidden)


def _leaves(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from _leaves(v)
    elif isinstance(node, list):
        for v in node:
            yield from _leaves(v)
    else:
        yield node


def test_numeric_copilot_is_read_only_offline_and_evidence_comes_from_stored_snapshot(rg_coach, rg_snap, rg_repo,
                                                                                     no_model_no_network):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rg_repo.seed_recommendation(run_id)
    stored = rg_repo.runs[run_id]['metrics_snapshot']
    values = list(_leaves(stored))
    before = state_of(rg_repo)
    seen = 0
    for action, kc in [('explain_priority', 'K1'), ('explain_priority', 'K3'), ('explain_priority', 'K2'),
                       ('explain_priority', 'K5'), ('compare_previous', None), ('compare_previous', 'K1')]:
        res = copilot(c, run_id, action, kc)
        assert res.status_code == 200 and res.json()['source'] == 'stored_snapshot'
        for item in res.json()['evidence']:
            assert item['value'] in values, (action, kc, item)  # mọi số trích dẫn đều có trong snapshot đã lưu
            seen += 1
    assert seen >= 6 and state_of(rg_repo) == before


@pytest.mark.parametrize('action,kc', [('review_plan_15m', None), ('recheck_questions', 'K1')])
@pytest.mark.parametrize('run_ai_status', ['not_enabled', 'ready', 'blocked', 'failed', None])
def test_ai_actions_stay_blocked_server_side_even_if_run_and_files_claim_ready(
        rg_coach, rg_snap, rg_repo, tmp_path, monkeypatch, no_model_no_network, action, kc, run_ai_status):
    kb, jev = tmp_path / 'kb.json', tmp_path / 'jev.json'
    kb.write_text('{"sources": []}'), jev.write_text('{"threshold": 0.8}')
    monkeypatch.setenv('LESSON_KB_PATH', str(kb))
    monkeypatch.setenv('JEV_CALIBRATION_PATH', str(jev))
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    rg_repo.runs[run_id]['ai_status'] = run_ai_status
    before = state_of(rg_repo)
    res = copilot(c, run_id, action, kc)
    assert res.status_code == 409 and res.json()['detail']['code'] == 'ai_unavailable'
    assert res.json()['detail']['reasons'] and 'evidence' not in res.json()['detail']
    assert state_of(rg_repo) == before


def test_ai_gate_cannot_be_opened_by_client_supplied_fields(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    run_id = create_run(c)
    for extra in ({'ai_enabled': True}, {'ai_status': 'ready'}, {'kb': 'x'}, {'force': True}):
        res = c.post(f'/api/analysis-runs/{run_id}/copilot', json={'action': 'review_plan_15m', **extra})
        assert res.status_code == 422
    res = c.post(f'/api/analysis-runs/{run_id}/copilot', json={'action': 'review_plan_15m'},
                 headers={'X-AI-Enabled': 'true'}, params={'ai': '1'})
    assert res.status_code == 409


def test_copilot_follows_the_stored_run_not_the_latest_run_of_same_lesson(rg_coach, rg_snap, rg_repo):
    c = rg_coach(COACH_A)
    old = create_run(c, 'L2', 'old')
    snap = json.loads(rg_snap.read_text(encoding='utf-8'))
    snap['generated_at'] = 'later'
    snap['lessons']['L2']['kcs'][0]['incorrect_rate'] = 0.9
    rg_snap.write_text(json.dumps(snap), encoding='utf-8')
    new = create_run(c, 'L2', 'new')
    assert '40.0%' in copilot(c, old, 'explain_priority', 'K1').json()['message']
    assert '90.0%' in copilot(c, new, 'explain_priority', 'K1').json()['message']


# --- (g) không có mã học viên ---

LEARNER_IDS = ['HV-SECRET-0001', 'hv.secret.0002@example.com', 'Nguyễn Văn Bí Mật', '20249999777', 'uuid-5f3c-secret-0005']


def _real_snapshot():
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    rows = []
    for lesson in ('L1', 'L2'):
        for kc in ('K1', 'K2'):
            for i in range(12):
                rows.append((lesson, kc, 1, i % 3 != 0, LEARNER_IDS[i % len(LEARNER_IDS)] + f'-{lesson}{kc}{i % 5}'))
    rows += [('L2', 'K1', 1, None, LEARNER_IDS[0] + '-ungraded'), ('L2', 'K1', 2, False, LEARNER_IDS[1] + '-retry')]
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', rows)
    return build_snapshot(db, generated_at='t')


def _no_learner_ids(text):
    return not any(token in text for token in ('HV-SECRET', 'hv.secret', 'Bí Mật', '20249999777', 'uuid-5f3c'))


def test_snapshot_has_no_learner_ids_in_values_or_keys():
    snap = _real_snapshot()
    text = json.dumps(snap, ensure_ascii=False)
    assert _no_learner_ids(text)

    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                yield from keys(v)
        elif isinstance(node, list):
            for v in node:
                yield from keys(v)
    assert not {k for k in keys(snap) if k.lower() in {'hv', 'learner_id', 'learner_ids', 'student_id', 'ma_hv', 'learners_list'}}


def test_no_learner_id_in_any_response_or_stored_row_or_export(rg_coach, rg_repo, tmp_path, monkeypatch):
    path = tmp_path / 'real.v2.json'
    path.write_text(json.dumps(_real_snapshot(), ensure_ascii=False), encoding='utf-8')
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_V2_PATH', str(path))
    c = rg_coach(COACH_A)
    chunks = [c.get('/api/dashboard').text, c.get('/api/dashboard', params={'lesson_id': 'L1'}).text]
    run_id = create_run(c, 'L2', 'priv')
    rec = rg_repo.seed_recommendation(run_id)
    chunks += [c.get(f'/api/analysis-runs/{run_id}').text, c.get('/api/analysis-runs').text,
               c.get(f'/api/analysis-runs/{run_id}/export').content.decode('utf-8'),
               copilot(c, run_id, 'explain_priority', 'K1').text, copilot(c, run_id, 'compare_previous').text,
               review(c, run_id, rec['id'], 1, 'accept').text, json.dumps(rg_repo.runs, default=str, ensure_ascii=False)]
    assert all(_no_learner_ids(chunk) for chunk in chunks)
    assert 'learners' in chunks[0] or 'learner' in chunks[2]  # chỉ có SỐ người, không có danh sách


# --- (h) nháp cũ thiếu metadata ---

LEGACY_SNAPSHOTS = [{}, None, [], {'L1': [{'kc_code': 'K1', 'incorrect_rate': 0.4}]}, {'unexpected': 'shape'}]


@pytest.mark.parametrize('snapshot', LEGACY_SNAPSHOTS, ids=['empty', 'null', 'list', 'old_format', 'unknown_shape'])
def test_legacy_draft_opens_lists_exports_and_copilot_declines_without_500(rg_coach, rg_repo, snapshot):
    c = rg_coach(COACH_A, raise_server_exceptions=False)
    legacy = rg_repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot=snapshot)
    for missing in ('request_id', 'snapshot_version', 'ai_status', 'ai_status_reason', 'version'):
        legacy.pop(missing, None)
        rg_repo.runs[legacy['id']].pop(missing, None)  # hàng cũ: cột chưa tồn tại hẳn, không chỉ là None
    rg_repo.recommendations.append({'id': 'r1', 'analysis_run_id': legacy['id'], 'kc_code': 'K1', 'priority': 1,
                                    'content': 'đề xuất cũ', 'citations': None})
    detail = c.get(f"/api/analysis-runs/{legacy['id']}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body['ai_status'] is None and body['request_id'] is None and body['snapshot_version'] is None
    assert {'ai_status', 'snapshot_version', 'request_id'} <= set(body['not_recorded'])
    assert body['recommendations'][0]['content'] == 'đề xuất cũ' and 'review_status' in body['recommendations'][0]['not_recorded']
    listing = c.get('/api/analysis-runs')
    assert listing.status_code == 200 and [i['run_id'] for i in listing.json()['items']] == [legacy['id']]
    export = c.get(f"/api/analysis-runs/{legacy['id']}/export")
    rows = csv_rows(export)
    assert rows[0] == HEADER and rows[1][0] == 'Báo cáo' and NOT_RECORDED in rows[1][12]
    assert any(r[0] == 'Đề xuất' and r[10] == NOT_RECORDED for r in rows)
    assert all(not _is_dangerous(cell) for row in rows for cell in row)
    assert all(row[4] == '' or row[0] != 'Báo cáo' for row in rows)  # không bịa số 0 cho số liệu chưa ghi nhận
    res = copilot(c, legacy['id'], 'compare_previous')
    assert res.status_code == 422 and res.json()['detail']['code'] == 'snapshot_unavailable'


def test_legacy_draft_does_not_claim_recorded_values_it_does_not_have(rg_coach, rg_repo):
    c = rg_coach(COACH_A)
    legacy = rg_repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot={})
    body = c.get(f"/api/analysis-runs/{legacy['id']}").json()
    assert body['snapshot']['data'] is None and body['snapshot']['format'] == 'not_recorded'
    assert body['evaluations'] == [] and body['reviews'] == []
    assert body['ai_status'] is None  # chưa ghi nhận, không phải 'not_enabled'


def test_legacy_recommendation_can_still_be_reviewed(rg_coach, rg_repo):
    c = rg_coach(COACH_A)
    legacy = rg_repo.seed_run(COACH_A['id'], lesson_id='L1', metrics_snapshot={})
    rg_repo.recommendations.append({'id': 'r-old', 'analysis_run_id': legacy['id'], 'kc_code': 'K1', 'priority': 1,
                                    'content': 'cũ', 'citations': [], 'version': 1, 'review_status': None})
    res = review(c, legacy['id'], 'r-old', 1, 'accept')
    assert res.status_code == 201 and res.json()['recommendation']['review_status'] == 'accepted'
    assert rg_repo.reviews[0]['status_before'] == 'pending'  # review_status NULL của nháp cũ = pending
