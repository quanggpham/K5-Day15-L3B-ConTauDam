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
EMBEDDING_BATCH_SIZE = 100  # ~100 x 384 số mỗi request; RPC nhận tối đa 500


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

    def _request(self, method: str, *, params=None, json=None, prefer: str | None = None,
                 path: str = TABLE) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers['Prefer'] = prefer
        try:
            with self._client_factory(timeout=self._timeout) as client:
                return client.request(method, f'{self._base}/{path}', params=params, json=json, headers=headers)
        except httpx.HTTPError:
            # Không nối exception gốc: có thể chứa URL/headers.
            raise RepositoryError('supabase_unreachable') from None

    def approved_documents(self) -> list[dict]:
        """Document đã duyệt, cache TTL. Lỗi mạng/schema -> RepositoryError (handler map 503)."""
        if self._cache and self._clock() - self._cache[0] < CACHE_TTL_SECONDS:
            return self._cache[1]
        rows = []
        for offset in range(0, MAX_APPROVED_DOCUMENTS + 1, 200):
            response = self._request('GET', params={'select': READ_COLUMNS, 'approved': 'eq.true',
                                                    'is_current': 'eq.true', 'order': 'id.asc',
                                                    'limit': '200', 'offset': str(offset)})
            if response.status_code >= 300:
                raise RepositoryError(f'supabase_status_{response.status_code}')
            try:
                batch = response.json()
            except ValueError:
                raise RepositoryError('supabase_bad_json') from None
            if not isinstance(batch, list):
                raise RepositoryError('supabase_bad_shape')
            rows.extend(batch)
            if len(rows) > MAX_APPROVED_DOCUMENTS:
                raise RepositoryError('knowledge_limit_exceeded')
            if len(batch) < 200:
                self._cache = (self._clock(), rows)
                return rows
        raise RepositoryError('knowledge_limit_exceeded')

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

    def _rpc(self, function: str, body: dict):
        response = self._request('POST', json=body, path=f'rpc/{function}')
        if response.status_code >= 300:
            raise RepositoryError(f'supabase_status_{response.status_code}')
        try:
            return response.json()
        except ValueError:
            raise RepositoryError('supabase_bad_json') from None

    def ingest_document(self, document_key: str, documents: list[dict]) -> int:
        """Nạp các đoạn của một tài liệu qua RPC ingest_knowledge_document (một transaction, giữ lịch sử).
        Đoạn mới nhận approved=false; đoạn cũ cùng tài liệu không còn trong lô thì thôi is_current."""
        rows = [{key: d[key] for key in ('id', 'lesson_id', 'kc_code', 'text', 'source')} for d in documents]
        result = self._rpc('ingest_knowledge_document', {'p_key': document_key, 'p_rows': rows, 'p_actor': None})
        self._cache = None
        return result

    def set_embeddings(self, model: str, vectors: dict[str, str]) -> int:
        """Ghi vector (dạng text pgvector) theo lô; trả số đoạn đã cập nhật."""
        items = sorted(vectors.items())
        updated = 0
        for start in range(0, len(items), EMBEDDING_BATCH_SIZE):
            rows = [{'id': chunk_id, 'embedding': vector} for chunk_id, vector in items[start:start + EMBEDDING_BATCH_SIZE]]
            updated += self._rpc('set_knowledge_embeddings', {'p_model': model, 'p_rows': rows})
        return updated

    def match_documents(self, embedding: str, lesson_id: str, kc_code: str, limit: int) -> list[dict]:
        """Đoạn đã duyệt gần nhất theo cosine trong đúng bài + KC (RPC match_knowledge_documents)."""
        rows = self._rpc('match_knowledge_documents', {'p_embedding': embedding, 'p_lesson_id': lesson_id,
                                                       'p_kc_code': kc_code, 'p_limit': limit})
        if not isinstance(rows, list):
            raise RepositoryError('supabase_bad_shape')
        return rows
