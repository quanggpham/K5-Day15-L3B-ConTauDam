from fastapi.testclient import TestClient
from codebase.backend.main import app


def test_protected_me_requires_token():
    assert TestClient(app).get('/api/me').status_code == 401


def test_me_enforces_verified_identity_and_allowlist(monkeypatch):
    import httpx
    from codebase.backend.security import auth
    monkeypatch.setenv('SUPABASE_URL', 'https://example.test')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'public')
    state = {'authenticated': True, 'allowed': False}
    def handler(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': 'user-id', 'email': 'coach@example.com'}) if state['authenticated'] else httpx.Response(401)
        return httpx.Response(200, json=state['allowed'])
    client_type = httpx.Client
    monkeypatch.setattr(auth.httpx, 'Client', lambda **kwargs: client_type(transport=httpx.MockTransport(handler), **kwargs))
    client = TestClient(app)
    headers = {'Authorization': 'Bearer example'}
    assert client.get('/api/me', headers=headers).status_code == 403
    state['allowed'] = True
    assert client.get('/api/me', headers=headers).json()['id'] == 'user-id'
    state['authenticated'] = False
    assert client.get('/api/me', headers=headers).status_code == 401
