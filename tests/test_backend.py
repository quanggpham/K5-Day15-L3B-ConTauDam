from fastapi.testclient import TestClient
from codebase.backend.main import app


def test_health_config_and_api_404(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "public-key")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "must-not-appear")
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/config").json() == {"supabase_url": "https://example.supabase.co", "supabase_publishable_key": "public-key"}
    assert client.get("/api/missing").status_code == 404
