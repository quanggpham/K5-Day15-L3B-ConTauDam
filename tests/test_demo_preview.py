import json

import pytest
from codebase.backend.api import demo_preview
from tests.test_reviews_copilot import COACH_A, COACH_B, _create, as_coach, snap_path, repo  # noqa: F401


def test_demo_requires_owner_approved_sources_and_safe_output(as_coach, snap_path, monkeypatch):
    monkeypatch.setenv('DEMO_AI_ENABLED', 'true')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'synthetic-test-key')
    client = as_coach(COACH_A)
    run_id = _create(client)
    url = f'/api/analysis-runs/{run_id}/demo-preview'
    sources = [{'id': 'doc-1', 'source': 'Synthetic lesson', 'lesson_id': 'L2', 'kc_code': 'K1', 'text': 'K1 examples', 'approved': True, 'is_current': True, 'reviewed_by': 'coach', 'reviewed_at': '2026-11-28'}]
    monkeypatch.setattr(demo_preview, 'load_sources', lambda lesson, kc: sources)
    def model(system, user):
        payload = json.loads(user)
        assert payload['evidence']['lesson_id'] == 'L2' and 'learner_count' not in payload['evidence']
        return {'text': json.dumps({'kc_code': 'K1', 'content': 'Ôn lại bằng ví dụ.', 'citations': ['doc-1']}),
                'model': 'lfm3-1.7b', 'tokens_in': 31, 'tokens_out': 22}
    monkeypatch.setattr(demo_preview, 'call_demo_model', model)
    def judge(evidence, proposal):
        assert evidence['sources'] == [{'id': 'doc-1', 'text': 'K1 examples'}]
        assert 'learner_count' not in evidence and proposal['citations'] == ['doc-1']
        return {'grounded': 0.9, 'relevant': 0.8}
    monkeypatch.setattr(demo_preview, 'score_demo_draft', judge)
    response = client.post(url, json={'kc_code': 'K1'})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'demo_unvalidated' and body['sources'][0]['id'] == 'doc-1'
    assert body['tokens_in'] == 31 and body['jev_score'] == {'grounded': 0.9, 'relevant': 0.8}
    save_url = url + '/save'
    ticket = {'token': body['save_token']}
    assert as_coach(COACH_B).post(save_url, json=ticket).status_code == 404
    as_coach(COACH_A)
    assert client.post(save_url, json={'token': body['save_token'] + '0'}).status_code == 422
    assert client.get(f'/api/analysis-runs/{run_id}').json()['recommendations'] == []
    saved = client.post(save_url, json=ticket)
    assert saved.status_code == 200
    assert client.post(save_url, json=ticket).json() == saved.json()
    detail = client.get(f'/api/analysis-runs/{run_id}').json()
    rec, = detail['recommendations']
    assert rec['content'] == body['content'] and rec['jev_score'] == body['jev_score']
    assert rec['citations'][0]['origin'] == 'demo_unvalidated'
    result = client.post(f'/api/analysis-runs/{run_id}/reviews', json={
        'recommendation_id': rec['id'], 'version': rec['version'], 'decision': 'accept'})
    assert result.status_code == 201 and result.json()['recommendation']['review_status'] == 'accepted'
    assert result.json()['recommendation']['jev_score'] == body['jev_score']
    result = client.post(f'/api/analysis-runs/{run_id}/reviews', json={
        'recommendation_id': rec['id'], 'version': result.json()['recommendation']['version'],
        'decision': 'reject'})
    assert result.status_code == 201 and result.json()['recommendation']['review_status'] == 'rejected'
    assert as_coach(COACH_B).post(url, json={'kc_code': 'K1'}).status_code == 404
    assert as_coach(COACH_A).post(url, json={'kc_code': 'K2'}).status_code == 422
    sources[0]['reviewed_at'] = None
    assert client.post(save_url, json=ticket).status_code == 409
    def unexpected(*args):
        raise AssertionError('unreviewed source reached the model')
    monkeypatch.setattr(demo_preview, 'call_demo_model', unexpected)
    assert client.post(url, json={'kc_code': 'K1'}).status_code == 409


def test_demo_rejects_bad_citations_and_provider_error(as_coach, snap_path, monkeypatch):
    monkeypatch.setenv('DEMO_AI_ENABLED', 'true')
    client = as_coach(COACH_A)
    run_id = _create(client)
    url = f'/api/analysis-runs/{run_id}/demo-preview'
    monkeypatch.setattr(demo_preview, 'load_sources', lambda *args: [
        {'id': 'doc-1', 'source': 'Synthetic lesson', 'lesson_id': 'L2', 'kc_code': 'K1', 'text': 'K1', 'approved': True, 'is_current': True, 'reviewed_by': 'coach', 'reviewed_at': '2026-11-28'}])
    monkeypatch.setattr(demo_preview, 'call_demo_model', lambda *args: {
        'text': json.dumps({'kc_code': 'K1', 'content': 'Nội dung', 'citations': ['fake']}),
        'model': 'x', 'tokens_in': 1, 'tokens_out': 1})
    assert client.post(url, json={'kc_code': 'K1'}).status_code == 502
    monkeypatch.delenv('DEMO_AI_ENABLED')
    assert client.post(url, json={'kc_code': 'K1'}).status_code == 503


def test_demo_rejects_source_revoked_during_model_call(as_coach, snap_path, monkeypatch):
    monkeypatch.setenv('DEMO_AI_ENABLED', 'true')
    client = as_coach(COACH_A)
    run_id = _create(client)
    source = {'id': 'doc-1', 'source': 'Synthetic lesson', 'lesson_id': 'L2', 'kc_code': 'K1', 'text': 'K1', 'approved': True, 'is_current': True, 'reviewed_by': 'coach', 'reviewed_at': '2026-11-28'}
    state = {'approved': True}
    monkeypatch.setattr(demo_preview, 'load_sources', lambda *args: [source] if state['approved'] else [])
    def model(*args):
        state['approved'] = False
        return {'text': json.dumps({'kc_code': 'K1', 'content': 'Example', 'citations': ['doc-1']}),
                'model': 'liquid', 'tokens_in': 1, 'tokens_out': 1}
    monkeypatch.setattr(demo_preview, 'call_demo_model', model)
    assert client.post(f'/api/analysis-runs/{run_id}/demo-preview', json={'kc_code': 'K1'}).status_code == 409


@pytest.mark.parametrize(('kind', 'content', 'expected'), [
    ('review_plan_15m', ['Giới thiệu khái niệm.', 'Làm ví dụ.', 'Thảo luận lỗi.'], '10–15 phút: Thảo luận lỗi.'),
    ('recheck_questions', [{'question': 'K1 là gì?', 'answer': 'Khái niệm.'},
                           {'question': 'Dùng khi nào?', 'answer': 'Khi ôn.'},
                           {'question': 'Vì sao cần biết?', 'answer': 'Để áp dụng.'}], 'Đáp án: Để áp dụng.'),
    ('recheck_questions', [{'question': 'K1 là gì?', 'answer': 'Khái niệm.'}], None),
])
def test_demo_actions_validate_and_format_drafts(kind, content, expected, as_coach, snap_path, monkeypatch):
    monkeypatch.setenv('DEMO_AI_ENABLED', 'true')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'synthetic-test-key')
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    client = as_coach(COACH_A)
    run_id = _create(client)
    monkeypatch.setattr(demo_preview, 'load_sources', lambda *args: [
        {'id': 'doc-1', 'source': 'Synthetic lesson', 'lesson_id': 'L2', 'kc_code': 'K1',
         'text': 'K1', 'approved': True, 'is_current': True, 'reviewed_by': 'coach', 'reviewed_at': '2026-11-28'}])
    monkeypatch.setattr(demo_preview, 'call_demo_model', lambda *args: {
        'text': json.dumps({'kc_code': 'K1', 'content': content, 'citations': ['doc-1']}),
        'model': 'test-model', 'tokens_in': 10, 'tokens_out': 5})
    url = f'/api/analysis-runs/{run_id}/demo-preview'
    result = client.post(url, json={'kc_code': 'K1', 'kind': kind})
    if expected is None:
        assert result.status_code == 502
    else:
        assert result.status_code == 200
        assert expected in result.json()['content']
        assert client.post(url + '/save', json={'token': result.json()['save_token']}).status_code == 200
        rec, = client.get(f'/api/analysis-runs/{run_id}').json()['recommendations']
        assert rec['content'] == result.json()['content']
