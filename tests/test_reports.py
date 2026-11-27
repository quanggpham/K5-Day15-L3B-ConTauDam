import json
from fastapi.testclient import TestClient
from codebase.backend.main import app
from codebase.backend.security.auth import require_coach


def test_reports_auth_and_missing_data(tmp_path, monkeypatch):
    target = tmp_path / 'aggregate.json'
    monkeypatch.setenv('AGGREGATE_SNAPSHOT_PATH', str(target))
    client = TestClient(app)
    assert client.get('/api/lessons').status_code == 401
    app.dependency_overrides[require_coach] = lambda: {'id': 'coach'}
    try:
        assert client.get('/api/lessons').status_code == 503
        target.write_text(json.dumps({'L1': [{'kc_code':'K1','insufficient_data':True}]}), encoding='utf-8')
        assert client.get('/api/lessons').json() == ['L1']
        assert client.get('/api/lessons/L1').json()['metrics'][0]['insufficient_data'] is True
        assert client.get('/api/lessons/L2').status_code == 404
    finally:
        app.dependency_overrides.clear()
