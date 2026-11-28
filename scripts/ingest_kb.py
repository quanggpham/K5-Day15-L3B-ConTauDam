"""Nạp Lesson KB (notes/quiz markdown) lên Supabase. Mặc định chỉ đếm; chỉ ghi khi có --apply.

Chạy local từ gốc repo, theo 3 bước:
  1) Đề xuất ánh xạ:  .venv/bin/python scripts/ingest_kb.py --notes DIR --quiz DIR --propose data/kb_mapping.csv
  2) Người duyệt sửa lesson_id/kc_code nếu cần và ghi confirmed=yes cho dòng đúng.
  3) Nạp:             .venv/bin/python scripts/ingest_kb.py --notes DIR --quiz DIR --mapping data/kb_mapping.csv [--apply]
Danh mục KC lấy từ snapshot v2 (--snapshot, mặc định data/aggregate.v2.json). --apply cần SUPABASE_URL và
SUPABASE_SERVICE_ROLE_KEY trong .env. Không in nội dung đoạn. Document mới luôn approved=false.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codebase.backend.rag.chunking import chunk_notes, chunk_quiz  # noqa: E402
from codebase.backend.rag.kb_mapping import (kc_catalog, load_mapping, propose_mapping,  # noqa: E402
                                             to_documents, write_mapping)
from codebase.backend.rag.ingestion import extract_chunks  # noqa: E402
from codebase.backend.rag.store import KnowledgeStore  # noqa: E402

DEFAULT_SNAPSHOT = Path('data/aggregate.v2.json')


def collect_chunks(notes_dir: Path | None, quiz_dir: Path | None, files_dir: Path | None = None) -> list[dict]:
    chunks: list[dict] = []
    for directory, chunker, prefix in ((notes_dir, chunk_notes, 'notes'), (quiz_dir, chunk_quiz, 'quiz')):
        if directory is None:
            continue
        for path in sorted(directory.glob('day*.md')):
            chunks += chunker(path.read_text(encoding='utf-8'), f'{prefix}/{path.stem}')
    if files_dir is not None:
        for path in sorted(files_dir.iterdir()):
            if path.is_file() and path.suffix.lower() in ('.md', '.pdf'):
                chunks += [{**chunk, 'source': path.name} for chunk in extract_chunks(path.name, path.read_bytes())]
    return chunks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--quiz', type=Path)
    parser.add_argument('--files', type=Path, help='thư mục PDF/Markdown trích xuất như giao diện web')
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_SNAPSHOT)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--propose', type=Path, help='ghi CSV đề xuất ánh xạ để người duyệt')
    action.add_argument('--mapping', type=Path, help='CSV ánh xạ đã duyệt (confirmed=yes)')
    parser.add_argument('--apply', action='store_true', help='ghi lên Supabase (cần --mapping và --confirm-rights)')
    parser.add_argument('--confirm-rights', action='store_true', help='xác nhận có quyền dùng và lưu tài liệu')
    args = parser.parse_args(argv)
    if not (args.notes or args.quiz or args.files):
        parser.error('cần --notes, --quiz hoặc --files')
    if args.apply and not args.mapping:
        parser.error('--apply cần --mapping')
    if args.apply and not args.confirm_rights:
        parser.error('--apply cần --confirm-rights để xác nhận quyền sử dụng tài liệu')

    chunks = collect_chunks(args.notes, args.quiz, args.files)
    print(f'{len(chunks)} đoạn từ {len({c["source"] for c in chunks})} nguồn')
    if not (args.propose or args.mapping):
        return 0
    catalog = kc_catalog(json.loads(args.snapshot.read_text(encoding='utf-8')))
    print(f'Danh mục: {len(catalog)} KC')

    if args.propose:
        write_mapping(propose_mapping(chunks, catalog), args.propose)
        print(f'Đã ghi đề xuất: {args.propose}. Duyệt rồi ghi confirmed=yes cho dòng đúng.')
        return 0

    documents, skipped = to_documents(chunks, load_mapping(args.mapping, catalog))
    print(f'{len(documents)} document đã xác nhận ánh xạ; {skipped} đoạn bị bỏ vì chưa xác nhận')
    if not args.apply:
        print('Dry-run: chưa ghi gì.')
        return 0
    load_dotenv()
    url, key = os.getenv('SUPABASE_URL', ''), os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not (url and key):
        print('Thiếu SUPABASE_URL hoặc SUPABASE_SERVICE_ROLE_KEY.', file=sys.stderr)
        return 2
    print(f'Đã upsert {KnowledgeStore(url, key).upsert_documents(documents)} document (approved=false cho dòng mới).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
