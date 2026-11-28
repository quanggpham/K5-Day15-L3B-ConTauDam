"""Xuất toàn bộ đoạn Lesson KB ra JSONL để embed ngoài backend (kaggle/embed_kb.py).

  .venv/bin/python scripts/export_kb_chunks.py --notes DIR --quiz DIR --mapping data/kb_mapping.csv \
      --out data/kb_chunks.jsonl

Lấy cả đoạn chưa xác nhận ánh xạ (lesson_id/kc_code theo đề xuất); khi nạp, mọi document vẫn approved=false.
Mỗi đoạn phải có dòng trong CSV ánh xạ (tạo bằng `ingest_kb.py --propose`). Không in nội dung đoạn.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codebase.backend.rag.kb_mapping import kc_catalog, load_mapping  # noqa: E402
from scripts.ingest_kb import DEFAULT_SNAPSHOT, collect_chunks  # noqa: E402

EXPORT_FIELDS = ('id', 'source', 'lesson_id', 'kc_code', 'text')


def build_export_rows(chunks: list[dict], mapping: dict[str, dict]) -> list[dict]:
    """Ghép đoạn với ánh xạ; thiếu ánh xạ hoặc id lặp -> ValueError (không bỏ qua im lặng)."""
    missing = [chunk['id'] for chunk in chunks if chunk['id'] not in mapping]
    if missing:
        raise ValueError(f'{len(missing)} đoạn chưa có dòng ánh xạ, ví dụ {missing[0]!r}; chạy lại --propose')
    ids = [chunk['id'] for chunk in chunks]
    if len(set(ids)) != len(ids):
        raise ValueError('id đoạn bị lặp')
    return [{field: {**chunk, **mapping[chunk['id']]}[field] for field in EXPORT_FIELDS} for chunk in chunks]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--notes', type=Path)
    parser.add_argument('--quiz', type=Path)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    if not (args.notes or args.quiz):
        parser.error('cần --notes hoặc --quiz')

    catalog = kc_catalog(json.loads(args.snapshot.read_text(encoding='utf-8')))
    mapping = load_mapping(args.mapping, catalog, include_unconfirmed=True)
    rows = build_export_rows(collect_chunks(args.notes, args.quiz), mapping)
    with args.out.open('w', encoding='utf-8') as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'Đã xuất {len(rows)} đoạn từ {len({r["source"] for r in rows})} nguồn -> {args.out}')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
