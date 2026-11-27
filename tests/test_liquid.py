import importlib
import sys
from pathlib import Path


def test_liquid_returns_real_usage(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / 'codebase'))
    ai = importlib.import_module('ai')
    monkeypatch.setattr(ai, 'MODEL_PROVIDER', 'liquid')
    monkeypatch.setattr(ai, 'MODEL_NAME', 'lfm3-1.7b')
    monkeypatch.setattr(ai, 'API_KEY', 'test-key')
    def fake_post(url, **kwargs):
        assert url == 'https://api.liquid.ai/openai/v1/chat/completions'
        assert kwargs['json']['model'] == 'lfm3-1.7b'
        class Response:
            def raise_for_status(self): pass
            def json(self): return {'model':'lfm3-1.7b','choices':[{'message':{'content':'ok'}}], 'usage':{'prompt_tokens':10,'completion_tokens':5}}
        return Response()
    import httpx
    monkeypatch.setattr(httpx, 'post', fake_post)
    assert ai.call_model('system','user') == {'text':'ok','model':'lfm3-1.7b','tokens_in':10,'tokens_out':5}
