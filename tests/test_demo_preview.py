import json
from codebase.backend.api import demo_preview
from tests.test_reviews_copilot import COACH_A, COACH_B, _create, as_coach, snap_path, repo  # noqa: F401


def test_demo_requires_owner_approved_sources_and_safe_output(as_coach, snap_path, monkeypatch):
    monkeypatch.setenv('DEMO_AI_ENABLED', 'true')
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
    response = client.post(url, json={'kc_code': 'K1'})
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'demo_unvalidated' and body['sources'][0]['id'] == 'doc-1'
    assert body['tokens_in'] == 31 and 'jev_score' not in body
    assert as_coach(COACH_B).post(url, json={'kc_code': 'K1'}).status_code == 404
    assert as_coach(COACH_A).post(url, json={'kc_code': 'K2'}).status_code == 422
    sources[0]['reviewed_at'] = None
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
