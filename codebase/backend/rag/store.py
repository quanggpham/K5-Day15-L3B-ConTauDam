"""Đọc/ghi Lesson KB trên Supabase (PostgREST, service role). Chỉ dùng ở backend và script ingest."""
import time
from collections.abc import Callable
from datetime import datetime, timezone

import httpx

from ..api.run_repository import RepositoryError

TABLE = 'knowledge_documents'
READ_COLUMNS = 'id,lesson_id,kc_code,text,approved'
CACHE_TTL_SECONDS = 300.0
MAX_APPROVED_DOCUMENTS = 5000  # chặn truy vấn không giới hạn; KB hiện chỉ cỡ vài nghìn đoạn
UPSERT_BATCH_SIZE = 200


class KnowledgeStore:
    def __init__(self, url: str, service_key: str, *, timeout: float = 10.0,
                 client_factory: Callable[..., httpx.Client] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._base = url.rstrip('/') + '/rest/v1'
        self._headers = {'apikey': service_key, 'Authorization': f'Bearer {service_key}'}
        self._timeout = timeout
        self._client_factory = client_factory or httpx.Client
        self._clock = clock
        self._now = now
        self._cache: tuple[float, list[dict]] | None = None

    def _request(self, method: str, *, params=None, json=None, prefer: str | None = None) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers['Prefer'] = prefer
        try:
            with self._client_factory(timeout=self._timeout) as client:
                return client.request(method, f'{self._base}/{TABLE}', params=params, json=json, headers=headers)
        except httpx.HTTPError:
            # Không nối exception gốc: có thể chứa URL/headers.
            raise RepositoryError('supabase_unreachable') from None

    def approved_documents(self) -> list[dict]:
        """Document đã duyệt, cache TTL. Lỗi mạng/schema -> RepositoryError (handler map 503)."""
        if self._cache and self._clock() - self._cache[0] < CACHE_TTL_SECONDS:
            return self._cache[1]
        response = self._request('GET', params={'select': READ_COLUMNS, 'approved': 'eq.true',
                                                'order': 'id.asc', 'limit': str(MAX_APPROVED_DOCUMENTS)})
        if response.status_code >= 300:
            raise RepositoryError(f'supabase_status_{response.status_code}')
        try:
            rows = response.json()
        except ValueError:
            raise RepositoryError('supabase_bad_json') from None
        if not isinstance(rows, list):
            raise RepositoryError('supabase_bad_shape')
        self._cache = (self._clock(), rows)
        return rows

    def upsert_documents(self, documents: list[dict]) -> int:
        """Upsert theo id, chia lô. Payload không có cột approved nên dòng đã duyệt giữ nguyên cờ
        và dòng mới nhận mặc định false."""
        now = self._now().isoformat()
        sent = 0
        for start in range(0, len(documents), UPSERT_BATCH_SIZE):
            batch = [{'id': d['id'], 'lesson_id': d['lesson_id'], 'kc_code': d['kc_code'], 'text': d['text'],
                      'source': d['source'], 'updated_at': now} for d in documents[start:start + UPSERT_BATCH_SIZE]]
            response = self._request('POST', params={'on_conflict': 'id'}, json=batch,
                                     prefer='resolution=merge-duplicates,return=minimal')
            if response.status_code >= 300:
                raise RepositoryError(f'supabase_status_{response.status_code}')
            sent += len(batch)
        self._cache = None
        return sent
