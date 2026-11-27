"""GET /api/analysis-runs/{id}/export: CSV UTF-8 (BOM) chỉ từ dữ liệu đã lưu của run.

Không đọc snapshot hiện tại, không tính lại. Chủ sở hữu lấy từ session; id lạ/của coach khác -> 404 như nhau.
Số thật (int/float) ghi nguyên dạng; MỌI ô văn bản (nội dung người dùng/model) đi qua `_safe_text` để bảng tính
không diễn giải thành công thức. Dữ liệu thiếu để trống hoặc ghi "chưa được ghi nhận", không thay bằng 0.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from codebase.backend.api.analysis_runs import NOT_RECORDED, RUN_SNAPSHOT_SCHEMA, _unavailable
from codebase.backend.api.run_repository import RepositoryError, RunRepository, get_run_repository
from codebase.backend.security.auth import require_coach

router = APIRouter()

BOM = '﻿'
NO_GRADED = 'không có lượt chấm'
SMALL_GROUP = 'ẩn: mẫu nhỏ (dưới 5 người)'  # KC có quá ít học viên: không xuất số để không lộ từng người
HEADER = ['Loại dòng', 'Mã bài', 'Mã KC', 'Trạng thái', 'Số lượt chấm (lượt)', 'Số người (người)',
          'Tỷ lệ sai (0-1, trên lượt chấm lần đầu)', 'Thứ hạng ưu tiên', 'Nội dung đề xuất', 'Nguồn/căn cứ',
          'Trạng thái duyệt', 'Nhận xét duyệt', 'Ghi chú']
_FORMULA_START = ('=', '+', '-', '@', '\t', '\r')
_FILENAME_UNSAFE = re.compile(r'[^A-Za-z0-9_-]')
_CITATION_KEYS = ('source_id', 'title', 'source', 'url')


def _safe_text(value) -> str:
    """Vô hiệu hoá công thức: ô bắt đầu (kể cả sau khoảng trắng) bằng = + - @ tab CR được thêm tiền tố '."""
    if value is None:
        return ''
    text = value if isinstance(value, str) else str(value)
    head = text.lstrip()
    if text[:1] in ('\t', '\r', '\n') or head[:1] in _FORMULA_START:
        return "'" + text
    return text


def _num(value, *, missing: str = NOT_RECORDED) -> str:
    """Số thật (không phải bool/NaN/inf) -> chuỗi số; None -> `missing`; kiểu khác -> văn bản đã vô hiệu hoá."""
    if value is None:
        return missing
    if isinstance(value, bool):
        return _safe_text(value)
    if isinstance(value, (int, float)):
        return str(value) if math.isfinite(value) else missing
    return _safe_text(value)


def _citations(citations) -> str:
    """Chỉ xuất căn cứ thật sự có; không có -> rỗng (không bịa)."""
    if not citations or not isinstance(citations, list):
        return ''
    parts = []
    for item in citations:
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            text = ' · '.join(str(item[k]) for k in _CITATION_KEYS if item.get(k) not in (None, ''))
            text = text or json.dumps(item, ensure_ascii=False, sort_keys=True)
        else:
            text = str(item)
        if text.strip():
            parts.append(text)
    return ' | '.join(parts)


def _note(pairs: list[tuple[str, object]]) -> str:
    return '; '.join(f'{k}={v}' for k, v in pairs if v not in (None, ''))


_TEXT_COLS = ('kind', 'lesson', 'kc', 'status')
_NUM_COLS = ('responses', 'learners', 'rate', 'rank')  # chuỗi đã dựng từ `_num`
_TAIL_COLS = ('content', 'citations', 'review', 'comment', 'note')
_COLS = _TEXT_COLS + _NUM_COLS + _TAIL_COLS  # đúng thứ tự HEADER


def _row(**cells) -> list[str]:
    """Ô văn bản đi qua `_safe_text`; ô số là chuỗi từ `_num` nên số hợp lệ (vd. -30.0) không bị tiền tố."""
    return [cells.get(k, '') if k in _NUM_COLS else _safe_text(cells.get(k)) for k in _COLS]


def _kc_rank(lesson: dict) -> dict:
    ranks = {}
    for item in lesson.get('priority') or []:
        if isinstance(item, dict) and item.get('kc_code') is not None and isinstance(item.get('rank'), int):
            ranks[item['kc_code']] = item['rank']
    return ranks


def _snapshot_rows(run: dict) -> list[list[str]]:
    stored = run.get('metrics_snapshot')
    base_note = [('snapshot_version', run.get('snapshot_version') or NOT_RECORDED),
                 ('trạng thái AI', run.get('ai_status') or NOT_RECORDED), ('model', run.get('model')),
                 ('ghi nhận lúc', run.get('created_at'))]
    if not stored:
        return [_row(kind='Báo cáo', lesson=run.get('lesson_id'), status=run.get('status') or NOT_RECORDED,
                     note=_note(base_note + [('số liệu', f'snapshot {NOT_RECORDED}')]))]
    if not (isinstance(stored, dict) and stored.get('schema') == RUN_SNAPSHOT_SCHEMA
            and isinstance(stored.get('lesson'), dict)):
        return [_row(kind='Báo cáo', lesson=run.get('lesson_id'), status=run.get('status') or NOT_RECORDED,
                     note=_note(base_note + [('số liệu', 'snapshot định dạng cũ, không quy đổi hay tính lại')]))]
    lesson = stored['lesson']
    sample = lesson.get('sample') if isinstance(lesson.get('sample'), dict) else {}
    lesson_status = lesson.get('status')
    rows = [_row(kind='Báo cáo', lesson=run.get('lesson_id'), status=run.get('status') or NOT_RECORDED,
                 responses=_num(sample.get('responses')), learners=_num(sample.get('learners')),
                 rate=_num(lesson.get('incorrect_rate'), missing=NO_GRADED if lesson_status == 'no_graded' else NOT_RECORDED),
                 note=_note(base_note + [('trạng thái số liệu bài', lesson_status),
                                         ('chưa chấm (lượt)', sample.get('ungraded')),
                                         ('chênh lệch so với bài trước (điểm %)', lesson.get('delta_vs_previous_pp')),
                                         ('ngưỡng mẫu tối thiểu (lượt)', stored.get('min_sample'))]))]
    ranks = _kc_rank(lesson)
    for kc in lesson.get('kcs') or []:
        if not isinstance(kc, dict):
            continue
        status = kc.get('status')
        rows.append(_row(
            kind='Số liệu KC', lesson=run.get('lesson_id'), kc=kc.get('kc_code'), status=status or NOT_RECORDED,
            responses=_num(kc.get('graded_count'), missing=SMALL_GROUP if status == 'small_group' else NOT_RECORDED),
            learners=_num(kc.get('learner_count'), missing=SMALL_GROUP if status == 'small_group' else NOT_RECORDED),
            rate=_num(kc.get('incorrect_rate'), missing={'no_graded': NO_GRADED, 'small_group': SMALL_GROUP}.get(
                status, NOT_RECORDED)),
            rank=_num(ranks.get(kc.get('kc_code')), missing='')))
    return rows


def _recommendation_rows(run: dict, recs: list[dict]) -> list[list[str]]:
    rows = []
    for rec in recs:
        # needs_rereview luôn true sau khi sửa (ràng buộc DB) nên không dùng làm nhãn "chờ duyệt": chỉ review_status
        # == 'edited' mới là đang chờ coach duyệt lại bản sửa tay.
        flags = [('bản đã sửa tay', 'có' if rec.get('is_edited') else None),
                 ('chờ duyệt lại', 'có' if rec.get('review_status') == 'edited' else None),
                 ('phiên bản', rec.get('version'))]
        rows.append(_row(kind='Đề xuất', lesson=run.get('lesson_id'), kc=rec.get('kc_code'),
                         rank=_num(rec.get('priority'), missing=''), content=rec.get('content'),
                         citations=_citations(rec.get('citations')),
                         review=rec.get('review_status') or NOT_RECORDED, note=_note(flags)))
    return rows


def _review_rows(run: dict, recs: list[dict], reviews: list[dict]) -> list[list[str]]:
    kc_by_rec = {r.get('id'): r.get('kc_code') for r in recs}
    rows = []
    for rv in reviews:
        rows.append(_row(kind='Lịch sử duyệt', lesson=run.get('lesson_id'), kc=kc_by_rec.get(rv.get('recommendation_id')),
                         content=rv.get('content_after'), review=rv.get('decision') or NOT_RECORDED,
                         comment=rv.get('comment'),
                         note=_note([('lúc', rv.get('at')), ('phiên bản', rv.get('new_version')),
                                     ('bản đã sửa tay', 'có' if rv.get('decision') == 'edited' else None)])))
    return rows


def build_csv(detail: dict) -> bytes:
    run, recs, reviews = detail['run'], detail.get('recommendations') or [], detail.get('reviews') or []
    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL, lineterminator='\r\n')
    writer.writerow(HEADER)
    writer.writerows(_snapshot_rows(run) + _recommendation_rows(run, recs) + _review_rows(run, recs, reviews))
    return (BOM + buffer.getvalue()).encode('utf-8')


def export_filename(run: dict) -> str:
    lesson = _FILENAME_UNSAFE.sub('_', str(run.get('lesson_id') or 'bai'))[:40]
    rid = _FILENAME_UNSAFE.sub('', str(run.get('id') or ''))[:8]
    return f'learningpulse-{lesson}-{rid or "run"}.csv'


@router.get('/api/analysis-runs/{run_id}/export')
def export_analysis_run(run_id: str, user: dict = Depends(require_coach),
                        repo: RunRepository = Depends(get_run_repository)):
    try:
        detail = repo.get_run_detail(user['id'], run_id)
    except RepositoryError:
        raise _unavailable() from None
    if detail is None:  # không tồn tại hoặc không thuộc coach: cùng một phản hồi
        raise HTTPException(404, 'Không tìm thấy báo cáo')
    return Response(build_csv(detail), media_type='text/csv; charset=utf-8', headers={
        'Content-Disposition': f'attachment; filename="{export_filename(detail["run"])}"',
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
