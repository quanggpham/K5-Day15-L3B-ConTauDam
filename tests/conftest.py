import pytest

from codebase.backend.api import knowledge
from codebase.backend.security import rate_limit


@pytest.fixture(autouse=True)
def _no_query_embedder(monkeypatch):
    """Không tải model embedding thật trong test; test tìm kiếm vector tự thay embedder giả."""
    monkeypatch.setattr(knowledge, 'query_embedder', lambda: None)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Bộ đếm hạn mức là trạng thái toàn cục: xoá trước/sau mỗi test để các test không ảnh hưởng nhau."""
    rate_limit.reset()
    yield
    rate_limit.reset()
