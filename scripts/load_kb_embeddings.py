"""Nạp đoạn Lesson KB + embedding lên Supabase. Mặc định chỉ kiểm tra; chỉ ghi khi có --apply.

  .venv/bin/python scripts/load_kb_embeddings.py --chunks data/kb_chunks.jsonl \
      --embeddings data/kb_embeddings.jsonl [--apply --confirm-rights]

Kiểm tra trước khi ghi: model, số chiều, số hữu hạn, đủ và không thừa id. --apply cần SUPABASE_URL và
SUPABASE_SERVICE_ROLE_KEY (đọc từ môi trường hoặc .env). Document mới luôn approved=false. Không in nội dung đoạn.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codebase.backend.rag.embedding import (EMBEDDING_MODEL, MAX_EMBEDDING_BATCH,  # noqa: E402
                                            to_vector_literal, validate_embeddings)
from codebase.backend.rag.store import KnowledgeStore  # noqa: E402


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding='utf-8') as file:
        return [json.loads(line) for line in file if line.strip()]


def group_by_source(chunks: list[dict]) -> dict[str, list[dict]]:
    """Mỗi file nguồn là một tài liệu (document_key) để RPC ingest giữ phiên bản theo tài liệu."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        groups[chunk['source']].append(chunk)
    oversized = [key for key, rows in groups.items() if len(rows) > MAX_EMBEDDING_BATCH]
    if oversized:
        raise ValueError(f'tài liệu {oversized[0]!r} có hơn {MAX_EMBEDDING_BATCH} đoạn; hãy tách nhỏ')
    return dict(sorted(groups.items()))


def load(store: KnowledgeStore, chunks: list[dict], vectors: dict[str, list[float]]) -> tuple[int, int]:
    """Nạp từng tài liệu rồi ghi vector; trả (số đoạn đã nạp, số đoạn đã có vector)."""
    ingested = sum(store.ingest_document(key, rows) for key, rows in group_by_source(chunks).items())
    embedded = store.set_embeddings(EMBEDDING_MODEL, {cid: to_vector_literal(v) for cid, v in vectors.items()})
    return ingested, embedded


def main(argv: list[str] | None = None, store_factory=KnowledgeStore) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--chunks', type=Path, required=True)
    parser.add_argument('--embeddings', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='ghi lên Supabase (cần --confirm-rights)')
    parser.add_argument('--confirm-rights', action='store_true', help='xác nhận có quyền dùng và lưu tài liệu')
    args = parser.parse_args(argv)
    if args.apply and not args.confirm_rights:
        parser.error('--apply cần --confirm-rights để xác nhận quyền sử dụng tài liệu')

    chunks = read_jsonl(args.chunks)
    vectors = validate_embeddings(read_jsonl(args.embeddings), {chunk['id'] for chunk in chunks})
    groups = group_by_source(chunks)
    print(f'{len(chunks)} đoạn, {len(groups)} tài liệu, {len(vectors)} embedding hợp lệ ({EMBEDDING_MODEL})')
    if not args.apply:
        print('Dry-run: chưa ghi gì.')
        return 0
    load_dotenv()
    url, key = os.getenv('SUPABASE_URL', ''), os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not (url and key):
        print('Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY.', file=sys.stderr)
        return 2
    ingested, embedded = load(store_factory(url, key), chunks, vectors)
    print(f'Đã nạp {ingested} đoạn (approved=false cho đoạn mới); {embedded} đoạn có embedding.')
    return 0 if embedded == len(vectors) else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
