"""Ánh xạ từng đoạn KB -> (lesson_id, kc_code).

Số ngày của notes/quiz không khớp chủ đề bài LearningPulse (vd notes day07 ~ program-day06), nên ánh xạ theo
từng đoạn. Máy chỉ ĐỀ XUẤT ứng viên bằng BM25 trên tên KC; người duyệt đánh dấu `confirmed=yes` trong CSV.
Ingest chỉ lấy dòng đã xác nhận, không đoán.
"""
import csv
import re
from pathlib import Path
from typing import TypedDict

from rank_bm25 import BM25Okapi

MAPPING_COLUMNS = ('chunk_id', 'lesson_id', 'kc_code', 'confirmed', 'score', 'alternatives', 'preview')
CANDIDATE_COUNT = 3
PREVIEW_CHARS = 120
MODULE_KC_MARKER = ':module-'  # KC cấp module: quá chung để đề xuất tự động, người duyệt vẫn chọn tay được


class KbTarget(TypedDict):
    lesson_id: str
    kc_code: str


def kc_catalog(snapshot_v2: dict) -> list[KbTarget]:
    """Danh mục (lesson_id, kc_code) từ snapshot v2, sắp xếp ổn định."""
    catalog = [{'lesson_id': lesson_id, 'kc_code': kc['kc_code']}
               for lesson_id, lesson in snapshot_v2.get('lessons', {}).items()
               for kc in lesson.get('kcs', []) if isinstance(kc.get('kc_code'), str)]
    return sorted(catalog, key=lambda t: (t['lesson_id'], t['kc_code']))


def _tokens(text: str) -> list[str]:
    return re.findall(r'[a-z0-9]+', text.casefold().replace('_', ' '))


def propose_mapping(chunks: list[dict], catalog: list[KbTarget]) -> list[dict]:
    """Mỗi đoạn một dòng đề xuất: KC điểm cao nhất + ứng viên kế tiếp. confirmed luôn để trống."""
    candidates = [t for t in catalog if MODULE_KC_MARKER not in t['kc_code']]
    if not candidates:
        raise ValueError('Danh mục KC rỗng')
    index = BM25Okapi([_tokens(t['kc_code']) for t in candidates])
    rows = []
    for chunk in chunks:
        scores = index.get_scores(_tokens(chunk['text']))
        ranked = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))[:CANDIDATE_COUNT]
        best = candidates[ranked[0]]
        rows.append({'chunk_id': chunk['id'], 'lesson_id': best['lesson_id'], 'kc_code': best['kc_code'],
                     'confirmed': '', 'score': f'{scores[ranked[0]]:.2f}',
                     'alternatives': '; '.join(candidates[i]['kc_code'] for i in ranked[1:]),
                     'preview': chunk['text'][:PREVIEW_CHARS].replace('\n', ' ')})
    return rows


def write_mapping(rows: list[dict], path: Path) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=MAPPING_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def load_mapping(path: Path, catalog: list[KbTarget]) -> dict[str, KbTarget]:
    """Đọc CSV đã duyệt; chỉ lấy dòng confirmed=yes. Cặp (lesson_id, kc_code) phải có trong danh mục."""
    known = {(t['lesson_id'], t['kc_code']) for t in catalog}
    with path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        missing = {'chunk_id', 'lesson_id', 'kc_code', 'confirmed'} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'{path}: thiếu cột {sorted(missing)}')
        mapping: dict[str, KbTarget] = {}
        for line, row in enumerate(reader, start=2):
            if row['confirmed'].strip().casefold() != 'yes':
                continue
            target = (row['lesson_id'].strip(), row['kc_code'].strip())
            if target not in known:
                raise ValueError(f'{path}:{line}: {target} không có trong danh mục KC')
            mapping[row['chunk_id'].strip()] = {'lesson_id': target[0], 'kc_code': target[1]}
    return mapping


def to_documents(chunks: list[dict], mapping: dict[str, KbTarget]) -> tuple[list[dict], int]:
    """Trả (documents chưa duyệt, số đoạn bị bỏ vì chưa xác nhận ánh xạ)."""
    documents = [{**chunk, **mapping[chunk['id']], 'approved': False} for chunk in chunks if chunk['id'] in mapping]
    return documents, len(chunks) - len(documents)
