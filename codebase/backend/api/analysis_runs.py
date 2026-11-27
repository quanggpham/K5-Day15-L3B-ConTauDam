"""POST/GET /api/analysis-runs: tạo bản nháp idempotent từ snapshot v2, danh sách keyset, chi tiết theo owner.

Owner luôn lấy từ session (require_coach -> user['id']); body cấm trường lạ nên client không gửi được owner.
Lịch sử đọc metrics_snapshot đã lưu lúc tạo, không tính lại từ snapshot hiện tại.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from codebase.backend.analytics.snapshot import read_snapshot_v2
from codebase.backend.api.lesson_view import UNITS, lesson_view
from codebase.backend.api.run_repository import (
    AI_STATUSES, EVALUATION_FIELDS, RECOMMENDATION_FIELDS, REVIEW_FIELDS, DuplicateRequestError, RepositoryError,
    RunRepository, get_run_repository)
from codebase.backend.security import rate_limit
from codebase.backend.security.auth import require_coach

router = APIRouter()

# Giữ '/1' (frontend so khớp đúng chuỗi này). Từ bản này `lesson` lưu theo LessonView (api/lesson_view.py);
# bản /1 cũ lưu nguyên bài của build_snapshot -> khi đọc chuẩn hoá bằng lesson_view (idempotent, chỉ suy từ
# chính dữ liệu đã lưu; thiếu số thì distribution=None, không điền 0).
RUN_SNAPSHOT_SCHEMA = 'analysis_run_snapshot/1'
DRAFT_STATUS = 'draft'
AI_NOT_ENABLED_REASON = 'Chưa có căn cứ bài giảng được phép (KB) và ngưỡng JEV; chưa bật đề xuất AI.'
NOT_RECORDED = 'chưa được ghi nhận'
MAX_LIMIT = 100
_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
_STATUS_RE = re.compile(r'^[a-z_]{1,32}$')
# Metadata có từ migration 000003; nháp cũ để NULL -> báo "chưa được ghi nhận", không suy diễn.
# `model` không nằm đây: NULL là hợp lệ khi AI chưa bật.
_TRACKED_FIELDS = ('request_id', 'snapshot_version', 'ai_status', 'ai_status_reason')


class CreateRunBody(BaseModel):
    model_config = ConfigDict(extra='forbid')  # không nhận user_id/owner từ client
    lesson_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=128)

    @field_validator('lesson_id', 'request_id')
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip() or _CONTROL.search(value):
            raise ValueError('không được rỗng hoặc chứa ký tự điều khiển')
        return value


def _unavailable() -> HTTPException:
    return HTTPException(503, 'Không truy cập được kho lưu báo cáo')


def capture_lesson_snapshot(lesson_id: str) -> tuple[dict, str] | None:
    """Chụp số liệu của một bài từ snapshot v2 -> (metrics_snapshot, snapshot_version); None nếu bài không có."""
    snapshot = read_snapshot_v2()
    if not snapshot:
        return None
    if lesson_id not in {c.get('lesson_id') for c in snapshot['catalog']}:
        return None
    lesson = snapshot['lessons'].get(lesson_id)
    if lesson is None:
        return None
    generated_at = snapshot.get('generated_at')
    version = f"v{snapshot['version']}:{generated_at}" if generated_at else f"v{snapshot['version']}"
    return ({'schema': RUN_SNAPSHOT_SCHEMA, 'snapshot_version': version, 'source_version': snapshot['version'],
             'generated_at': generated_at, 'min_sample': snapshot.get('min_sample'), 'units': UNITS,
             'lesson': lesson_view(lesson)}, version)


def create_run(repo: RunRepository, owner_id: str, lesson_id: str, request_id: str) -> tuple[dict, bool]:
    """Idempotent theo (owner, request_id). Trả (run, created). Raise HTTPException 404/409/503."""
    def replay(existing: dict) -> tuple[dict, bool]:
        if existing['lesson_id'] != lesson_id:
            raise HTTPException(409, 'request_id đã dùng cho bài học khác')
        return existing, False

    try:
        existing = repo.find_by_request(owner_id, request_id)
        if existing is not None:
            return replay(existing)  # retry: không chụp lại snapshot, giữ dữ liệu lúc tạo
        captured = capture_lesson_snapshot(lesson_id)
        if captured is None:
            raise HTTPException(404, 'Không có dữ liệu cho bài học')
        metrics_snapshot, snapshot_version = captured
        wait = rate_limit.try_acquire(owner_id)  # chỉ tính lần tạo mới; retry/replay ở trên không bị tính
        if wait is not None:
            raise HTTPException(429, 'Tạo báo cáo quá nhanh, vui lòng thử lại sau',
                                headers={'Retry-After': str(int(wait) + 1)})
        row = {'lesson_id': lesson_id, 'request_id': request_id, 'status': DRAFT_STATUS,
               'metrics_snapshot': metrics_snapshot, 'snapshot_version': snapshot_version,
               'ai_status': 'not_enabled', 'ai_status_reason': AI_NOT_ENABLED_REASON, 'model': None}
        try:
            return repo.insert_run(owner_id, row), True
        except DuplicateRequestError:
            rate_limit.refund(owner_id)  # không tạo run mới nên không tính vào hạn mức
            # Race: request song song cùng request_id đã ghi trước -> đọc lại bản đó.
            winner = repo.find_by_request(owner_id, request_id)
            if winner is None:
                raise _unavailable() from None
            return replay(winner)
        except RepositoryError:
            rate_limit.refund(owner_id)  # ghi lỗi hạ tầng: coach không mất lượt
            raise
    except RepositoryError:
        raise _unavailable() from None


def _not_recorded(run: dict) -> list[str]:
    missing = [f for f in _TRACKED_FIELDS if run.get(f) is None]
    snap = run.get('metrics_snapshot')
    if 'metrics_snapshot' in run and not snap:
        missing.append('metrics_snapshot')
    return missing


def _summary(run: dict) -> dict:
    return {'run_id': run['id'], 'lesson_id': run['lesson_id'], 'status': run.get('status'),
            'ai_status': run.get('ai_status'), 'ai_status_reason': run.get('ai_status_reason'),
            'snapshot_version': run.get('snapshot_version'), 'request_id': run.get('request_id'),
            'model': run.get('model'), 'version': run.get('version'),
            'created_at': run.get('created_at'), 'updated_at': run.get('updated_at'),
            'not_recorded': [f for f in _TRACKED_FIELDS if run.get(f) is None]}


def _snapshot_view(stored) -> dict:
    if not stored:
        return {'format': 'not_recorded', 'data': None, 'notice': f'Snapshot số liệu {NOT_RECORDED}.'}
    if isinstance(stored, dict) and stored.get('schema') == RUN_SNAPSHOT_SCHEMA:
        data = stored
        if isinstance(stored.get('lesson'), dict):
            data = {**stored, 'lesson': lesson_view(stored['lesson'])}  # nháp /1 cũ thiếu khoá LessonView
        return {'format': RUN_SNAPSHOT_SCHEMA, 'data': data, 'notice': None}
    return {'format': 'legacy', 'data': stored,
            'notice': 'Snapshot định dạng cũ: hiển thị nguyên trạng, không quy đổi hay tính lại.'}


def _recommendation_view(rec: dict) -> dict:
    """Allowlist (RECOMMENDATION_FIELDS) — không trả nguyên dòng DB/RPC."""
    missing = [f for f in ('review_status',) if rec.get(f) is None]
    return {**{k: rec.get(k) for k in RECOMMENDATION_FIELDS}, 'not_recorded': missing}


def _evaluation_view(row: dict) -> dict:
    return {k: row.get(k) for k in EVALUATION_FIELDS}


def _review_view(review: dict) -> dict:
    return {k: review.get(k) for k in REVIEW_FIELDS}  # không có actor_email


def _encode_cursor(run: dict) -> str:
    raw = json.dumps({'c': run['created_at'], 'i': run['id']}, separators=(',', ':')).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip('=')


# Dạng PostgREST nhận cho timestamptz; fromisoformat của Python 3.11+ nhận thêm dạng lạ (vd tuần ISO).
_CURSOR_TS = re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})')


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        if len(cursor) > 512:
            raise ValueError
        data = json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4)))
        created_at, run_id = data['c'], data['i']
        if not isinstance(created_at, str) or not isinstance(run_id, str) or len(created_at) > 64 or len(run_id) > 64:
            raise ValueError
        if not _CURSOR_TS.fullmatch(created_at) or datetime.fromisoformat(created_at).tzinfo is None:
            raise ValueError
        uuid.UUID(run_id)
        return created_at, run_id
    except (ValueError, KeyError, TypeError, AttributeError, binascii.Error):
        raise HTTPException(422, 'cursor không hợp lệ') from None


@router.post('/api/analysis-runs', status_code=201)
def post_analysis_run(body: CreateRunBody, response: Response, user: dict = Depends(require_coach),
                      repo: RunRepository = Depends(get_run_repository)):
    run, created = create_run(repo, user['id'], body.lesson_id, body.request_id)
    if not created:
        response.status_code = 200
    return {**_summary(run), 'created': created}


@router.get('/api/analysis-runs')
def list_analysis_runs(user: dict = Depends(require_coach), repo: RunRepository = Depends(get_run_repository),
                       lesson_id: str | None = Query(default=None, min_length=1, max_length=200),
                       status: str | None = Query(default=None, max_length=32),
                       ai_status: str | None = Query(default=None, max_length=32),
                       limit: int = Query(default=20, ge=1, le=MAX_LIMIT),
                       cursor: str | None = Query(default=None, max_length=512)):
    if status is not None and not _STATUS_RE.fullmatch(status):
        raise HTTPException(422, 'status không hợp lệ')
    if ai_status is not None and ai_status not in (*AI_STATUSES, 'not_recorded'):
        raise HTTPException(422, 'ai_status không hợp lệ')
    after = _decode_cursor(cursor) if cursor else None
    try:
        rows = repo.list_runs(user['id'], lesson_id=lesson_id, status=status, ai_status=ai_status,
                              limit=limit + 1, after=after)
    except RepositoryError:
        raise _unavailable() from None
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]) if len(rows) > limit and page else None
    return {'items': [_summary(r) for r in page], 'next_cursor': next_cursor, 'limit': limit}


@router.get('/api/analysis-runs/{run_id}')
def get_analysis_run(run_id: str, user: dict = Depends(require_coach),
                     repo: RunRepository = Depends(get_run_repository)):
    try:
        detail = repo.get_run_detail(user['id'], run_id)
    except RepositoryError:
        raise _unavailable() from None
    if detail is None:  # không tồn tại hoặc không thuộc coach: cùng một phản hồi
        raise HTTPException(404, 'Không tìm thấy báo cáo')
    run = detail['run']
    return {**_summary(run), 'not_recorded': _not_recorded(run), 'not_recorded_label': NOT_RECORDED,
            'snapshot': _snapshot_view(run.get('metrics_snapshot')),
            'recommendations': [_recommendation_view(r) for r in detail['recommendations']],
            'evaluations': [_evaluation_view(e) for e in detail['evaluations']],
            'reviews': [_review_view(v) for v in detail['reviews']]}
