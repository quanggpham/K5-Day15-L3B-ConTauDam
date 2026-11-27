"""Giới hạn tần suất đơn giản theo coach (cửa sổ trượt, trong bộ nhớ một tiến trình).

Đủ cho một service Railway; nếu chạy nhiều bản sao thì cần kho dùng chung hoặc giới hạn ở proxy.
"""
import os
import threading
import time
from collections import defaultdict, deque

WINDOW_SECONDS = 60.0
DEFAULT_CREATES_PER_WINDOW = 20

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def creates_per_window() -> int:
    try:
        return max(1, int(os.getenv("RUN_CREATE_LIMIT_PER_MIN", DEFAULT_CREATES_PER_WINDOW)))
    except ValueError:
        return DEFAULT_CREATES_PER_WINDOW


def try_acquire(key: str, now: float | None = None) -> float | None:
    """Ghi một lượt. Trả None nếu được phép; nếu vượt hạn mức trả số giây nên chờ (Retry-After)."""
    now = time.monotonic() if now is None else now
    limit = creates_per_window()
    with _lock:
        hits = _hits[key]
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            return max(1.0, WINDOW_SECONDS - (now - hits[0]))
        hits.append(now)
        return None


def reset() -> None:
    with _lock:
        _hits.clear()
