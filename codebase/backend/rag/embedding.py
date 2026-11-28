"""Embedding cho Lesson KB: hằng số model, kiểm tra vector nạp vào, và embed câu truy vấn lúc chạy.

Vector đoạn bài giảng được tính một lần ngoài backend (kaggle/embed_kb.py) với tiền tố `passage: `;
câu truy vấn phải dùng đúng model đó với tiền tố `query: ` (quy ước của họ e5).
"""
import functools
import math
from collections.abc import Callable

EMBEDDING_MODEL = 'intfloat/multilingual-e5-small'
EMBEDDING_DIMENSIONS = 384  # khớp extensions.vector(384) trong migration 20261128000007
QUERY_PREFIX = 'query: '
PASSAGE_PREFIX = 'passage: '
MAX_EMBEDDING_BATCH = 500  # khớp giới hạn của RPC set_knowledge_embeddings

QueryEmbedder = Callable[[str], list[float]]


def validate_embeddings(rows: list[dict], expected_ids: set[str]) -> dict[str, list[float]]:
    """Kiểm tra file embeddings trước khi nạp: đúng model, đúng số chiều, số hữu hạn, đủ và không thừa id.

    Trả {chunk_id: vector}. Sai bất kỳ điều kiện nào -> ValueError nêu dòng và lý do.
    """
    vectors: dict[str, list[float]] = {}
    for line, row in enumerate(rows, start=1):
        chunk_id, vector = row.get('id'), row.get('embedding')
        if row.get('model') != EMBEDDING_MODEL:
            raise ValueError(f'dòng {line}: model {row.get("model")!r}, cần {EMBEDDING_MODEL!r}')
        if not isinstance(chunk_id, str) or chunk_id not in expected_ids:
            raise ValueError(f'dòng {line}: id {chunk_id!r} không có trong file chunk')
        if chunk_id in vectors:
            raise ValueError(f'dòng {line}: id {chunk_id!r} bị lặp')
        if not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSIONS:
            raise ValueError(f'dòng {line}: embedding phải có {EMBEDDING_DIMENSIONS} chiều')
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in vector):
            raise ValueError(f'dòng {line}: embedding có giá trị không phải số hữu hạn')
        vectors[chunk_id] = [float(x) for x in vector]
    missing = expected_ids - vectors.keys()
    if missing:
        raise ValueError(f'thiếu embedding cho {len(missing)} đoạn, ví dụ {sorted(missing)[0]!r}')
    return vectors


def to_vector_literal(vector: list[float]) -> str:
    """Định dạng text mà pgvector nhận khi truyền qua JSON (PostgREST/RPC)."""
    return '[' + ','.join(repr(float(x)) for x in vector) + ']'


@functools.cache
def load_query_embedder() -> QueryEmbedder | None:
    """Model embed câu truy vấn, nạp một lần. Trả None khi chưa cài extra `embed` để gọi nơi khác dùng BM25."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    model = SentenceTransformer(EMBEDDING_MODEL)

    def embed(query: str) -> list[float]:
        return model.encode(QUERY_PREFIX + query, normalize_embeddings=True).tolist()

    return embed
