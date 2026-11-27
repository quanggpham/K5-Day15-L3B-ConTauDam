import pytest

from codebase.backend.security import rate_limit


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Bộ đếm hạn mức là trạng thái toàn cục: xoá trước/sau mỗi test để các test không ảnh hưởng nhau."""
    rate_limit.reset()
    yield
    rate_limit.reset()
