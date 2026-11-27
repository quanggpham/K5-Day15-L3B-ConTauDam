"""Repository cho analysis_runs: tách lưu trữ khỏi handler.

Bất biến: MỌI truy vấn đều lọc theo owner_id (lấy từ session ở handler). Bản Supabase dùng service role
(bypass RLS) nên việc lọc owner ở code là lớp bảo vệ duy nhất -> không có method nào đọc/ghi mà không nhận owner_id.
Service role key chỉ đọc từ env SUPABASE_SERVICE_ROLE_KEY ở backend; không trả ra API, không log, không đưa vào lỗi.
"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Callable, Protocol

import httpx
from fastapi import HTTPException

AI_STATUSES = ('not_enabled', 'blocked', 'ready', 'failed')
RUN_SUMMARY_COLUMNS = ('id,user_id,lesson_id,request_id,status,ai_status,ai_status_reason,snapshot_version,'
                       'model,version,created_at,updated_at')
RUN_COLUMNS = RUN_SUMMARY_COLUMNS + ',metrics_snapshot'
RECOMMENDATION_COLUMNS = ('id,analysis_run_id,kc_code,priority,content,citations,version,review_status,'
                          'is_edited,needs_rereview,jev_score,updated_at')
EVALUATION_COLUMNS = 'id,analysis_run_id,metrics,judge,passed'
REVIEW_COLUMNS = ('id,run_id,recommendation_id,expected_version,new_version,decision,comment,content_before,'
                  'content_after,needs_rereview,actor_id,at,status_before,status_after')  # cột status_*: migration 000004
# Allowlist trường trả ra API (handler) và trong jsonb của RPC (migration 000004, test đối chiếu văn bản SQL).
RECOMMENDATION_FIELDS = tuple(RECOMMENDATION_COLUMNS.split(','))
EVALUATION_FIELDS = tuple(EVALUATION_COLUMNS.split(','))
REVIEW_FIELDS = tuple(REVIEW_COLUMNS.split(','))  # không có actor_email
REVIEW_RPC = 'review_recommendation'
CHILD_LIMIT = 1000  # chặn truy vấn bảng con không giới hạn; một run chỉ có vài đề xuất

DECISIONS = ('accept', 'reject', 'request_changes', 'edited')
DECISION_STATUS = {'accept': 'accepted', 'reject': 'rejected', 'request_changes': 'changes_requested',
                   'edited': 'edited'}
# Máy trạng thái duyệt (review_status NULL = 'pending'). PHẢI khớp hàm SQL public.review_recommendation
# (migration 20261127000004); test đối chiếu hai bên.
REVIEW_TRANSITIONS: dict[str, tuple[str, ...]] = {
    'pending': ('accept', 'reject', 'request_changes'),
    'accepted': ('reject', 'request_changes'),
    'rejected': ('accept', 'request_changes'),
    'changes_requested': ('edited', 'reject'),
    'edited': ('accept', 'reject', 'request_changes', 'edited'),
}
REVIEW_OUTCOMES = ('ok', 'replayed', 'not_found', 'version_conflict', 'invalid_transition', 'invalid_input')


class RepositoryError(Exception):
    """Kho lưu trữ không dùng được (mạng, timeout, 5xx, schema chưa migrate). Handler map -> 503."""


class DuplicateRequestError(Exception):
    """Vi phạm unique (user_id, request_id): có request song song đã ghi trước."""


class RunRepository(Protocol):
    def find_by_request(self, owner_id: str, request_id: str) -> dict | None: ...

    def insert_run(self, owner_id: str, row: dict) -> dict:
        """Ghi một run mới cho owner. Raise DuplicateRequestError khi trùng (owner, request_id)."""

    def list_runs(self, owner_id: str, *, lesson_id: str | None = None, status: str | None = None,
                  ai_status: str | None = None, limit: int = 20,
                  after: tuple[str, str] | None = None) -> list[dict]:
        """Sắp created_at desc, id desc; `after`=(created_at, id) là keyset cursor (loại trừ)."""

    def get_run(self, owner_id: str, run_id: str) -> dict | None:
        """None khi không tồn tại HOẶC không thuộc owner (không phân biệt hai trường hợp)."""

    def get_run_detail(self, owner_id: str, run_id: str) -> dict | None:
        """{'run','recommendations','evaluations','reviews'} hoặc None (giống get_run)."""

    def apply_review(self, owner_id: str, run_id: str, *, recommendation_id: str, expected_version: int,
                     decision: str, comment: str | None, content: str | None,
                     actor_email: str | None) -> dict:
        """Nguyên tử: kiểm owner + version + máy trạng thái, cập nhật đề xuất, bump version, ghi audit.

        Trả {'outcome': một trong REVIEW_OUTCOMES, 'recommendation'?: dòng hiện tại/sau, 'review'?: dòng audit}.
        'replayed' CHỈ khi audit khớp request VÀ audit.new_version == version hiện tại; còn lại 'version_conflict'.
        Hoặc cả hai thay đổi cùng được ghi, hoặc không gì cả. Raise RepositoryError khi kho lỗi.
        """


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


class InMemoryRunRepository:
    """Fake dùng cho test. Mô phỏng unique index (user_id, request_id) và thứ tự keyset của Postgres."""

    def __init__(self, clock: Callable[[], str] = _now):
        self._lock = threading.Lock()
        self._clock = clock
        self.runs: dict[str, dict] = {}
        self.recommendations: list[dict] = []
        self.evaluations: list[dict] = []
        self.reviews: list[dict] = []
        self.before_insert: Callable[[str, dict], None] | None = None  # hook mô phỏng race trong test
        self.before_review: Callable[[str, int], None] | None = None  # chạy trước khi lấy khoá (race test)
        self.before_review_commit: Callable[[dict, dict], None] | None = None  # raise = rollback

    def find_by_request(self, owner_id, request_id):
        with self._lock:
            return next((dict(r) for r in self.runs.values()
                         if r['user_id'] == owner_id and r.get('request_id') == request_id), None)

    def insert_run(self, owner_id, row):
        if self.before_insert:
            self.before_insert(owner_id, row)
        with self._lock:
            rid = row.get('request_id')
            if rid is not None and any(r['user_id'] == owner_id and r.get('request_id') == rid
                                       for r in self.runs.values()):
                raise DuplicateRequestError()
            now = self._clock()
            stored = {'model': None, 'status': 'pending', 'metrics_snapshot': {}, 'request_id': None,
                      'snapshot_version': None, 'ai_status': None, 'ai_status_reason': None,
                      **row, 'id': str(uuid.uuid4()), 'user_id': owner_id, 'version': 1,
                      'created_at': row.get('created_at') or now, 'updated_at': row.get('created_at') or now}
            self.runs[stored['id']] = stored
            return dict(stored)

    def seed_run(self, owner_id: str, **fields) -> dict:
        """Chèn run kiểu cũ (vd. thiếu metadata) cho test, bỏ qua kiểm tra idempotency."""
        with self._lock:
            row = {'id': str(uuid.uuid4()), 'user_id': owner_id, 'lesson_id': 'L1', 'metrics_snapshot': {},
                   'status': 'pending', 'model': None, 'request_id': None, 'snapshot_version': None,
                   'ai_status': None, 'ai_status_reason': None, 'version': 1,
                   'created_at': self._clock(), **fields}
            row.setdefault('updated_at', row['created_at'])
            self.runs[row['id']] = row
            return dict(row)

    def list_runs(self, owner_id, *, lesson_id=None, status=None, ai_status=None, limit=20, after=None):
        with self._lock:
            rows = [dict(r) for r in self.runs.values() if r['user_id'] == owner_id]
        if lesson_id is not None:
            rows = [r for r in rows if r['lesson_id'] == lesson_id]
        if status is not None:
            rows = [r for r in rows if r['status'] == status]
        if ai_status == 'not_recorded':
            rows = [r for r in rows if r.get('ai_status') is None]
        elif ai_status is not None:
            rows = [r for r in rows if r.get('ai_status') == ai_status]
        rows.sort(key=lambda r: (r['created_at'], r['id']), reverse=True)
        if after is not None:
            rows = [r for r in rows if (r['created_at'], r['id']) < after]
        return [{k: v for k, v in r.items() if k != 'metrics_snapshot'} for r in rows[:limit]]

    def get_run(self, owner_id, run_id):
        with self._lock:
            row = self.runs.get(run_id)
            return dict(row) if row and row['user_id'] == owner_id else None

    def get_run_detail(self, owner_id, run_id):
        run = self.get_run(owner_id, run_id)
        if run is None:
            return None
        with self._lock:
            recs = sorted((dict(r) for r in self.recommendations if r['analysis_run_id'] == run_id),
                          key=lambda r: (r['priority'], r['id']))
            evals = sorted((dict(e) for e in self.evaluations if e['analysis_run_id'] == run_id), key=lambda e: e['id'])
            reviews = sorted((dict(v) for v in self.reviews if v['run_id'] == run_id), key=lambda v: (v['at'], v['id']))
        return {'run': run, 'recommendations': recs, 'evaluations': evals, 'reviews': reviews}

    def seed_recommendation(self, run_id: str, **fields) -> dict:
        """Chèn đề xuất cho test (mặc định chưa duyệt, version 1)."""
        with self._lock:
            row = {'id': str(uuid.uuid4()), 'analysis_run_id': run_id, 'kc_code': 'K1', 'priority': 1,
                   'content': 'nội dung', 'citations': [], 'version': 1, 'review_status': None,
                   'is_edited': False, 'needs_rereview': False, 'jev_score': None,
                   'updated_at': self._clock(), **fields}
            self.recommendations.append(row)
            return dict(row)

    def apply_review(self, owner_id, run_id, *, recommendation_id, expected_version, decision, comment,
                     content, actor_email):
        """Mô phỏng hàm SQL review_recommendation: một khoá = một transaction (FOR UPDATE + version guard).

        Thay đổi được dựng trên bản sao; `before_review_commit` (hook test) chạy trước khi ghi -> raise ở đó
        mô phỏng transaction rollback: không đổi đề xuất, không có dòng audit.
        """
        if self.before_review:
            self.before_review(recommendation_id, expected_version)
        edited = decision == 'edited'
        if (decision not in DECISIONS or expected_version < 1 or (comment is not None and len(comment) > 2000)
                or (edited and (content is None or not content.strip() or len(content) > 4000))
                or (not edited and content is not None)):
            return {'outcome': 'invalid_input'}
        with self._lock:
            run = self.runs.get(run_id)
            if run is None or run['user_id'] != owner_id:
                return {'outcome': 'not_found'}
            index = next((i for i, r in enumerate(self.recommendations)
                          if r['id'] == recommendation_id and r['analysis_run_id'] == run_id), None)
            if index is None:
                return {'outcome': 'not_found'}
            current = self.recommendations[index]
            if current.get('version', 1) != expected_version:
                replay = next((v for v in reversed(self.reviews)
                               if v['recommendation_id'] == recommendation_id and v['run_id'] == run_id
                               and v['expected_version'] == expected_version and v['actor_id'] == owner_id
                               # chỉ replay khi chính lần ghi đó còn là trạng thái hiện tại (không bị ghi đè)
                               and v.get('new_version') == current.get('version', 1)
                               and v['decision'] == decision and v.get('comment') == comment
                               and (not edited or v.get('content_after') == content)), None)
                if replay is not None:
                    return {'outcome': 'replayed', 'recommendation': dict(current), 'review': dict(replay)}
                return {'outcome': 'version_conflict', 'recommendation': dict(current)}
            status = current.get('review_status') or 'pending'
            if decision not in REVIEW_TRANSITIONS.get(status, ()):
                return {'outcome': 'invalid_transition', 'recommendation': dict(current)}
            now = self._clock()
            updated = {**current, 'version': expected_version + 1, 'review_status': DECISION_STATUS[decision],
                       'updated_at': now}
            if edited:
                updated.update(content=content, is_edited=True, needs_rereview=True, jev_score=None)
            review = {'id': str(uuid.uuid4()), 'run_id': run_id, 'recommendation_id': recommendation_id,
                      'expected_version': expected_version, 'new_version': updated['version'],
                      'decision': decision, 'comment': comment, 'content_before': current.get('content'),
                      'content_after': updated.get('content'), 'needs_rereview': bool(updated.get('needs_rereview')),
                      'actor_id': owner_id, 'actor_email': actor_email, 'at': now,
                      'status_before': status, 'status_after': updated['review_status']}
            if self.before_review_commit:
                self.before_review_commit(updated, review)
            self.recommendations[index] = updated
            self.reviews.append(review)
            return {'outcome': 'ok', 'recommendation': dict(updated), 'review': dict(review)}


def _pick(row: dict, fields: tuple[str, ...]) -> dict:
    return {k: row.get(k) for k in fields}


def _quote(value: str) -> str:
    """Giá trị trong cú pháp or=(...) của PostgREST: bọc nháy kép, escape \\ và "."""
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


class SupabaseRunRepository:
    """PostgREST với service role. Chỉ dùng ở backend; luôn thêm user_id=eq.<owner> vào mọi truy vấn."""

    def __init__(self, url: str, service_key: str, timeout: float = 10.0,
                 client_factory: Callable[..., httpx.Client] | None = None):
        self._base = url.rstrip('/') + '/rest/v1'
        self._headers = {'apikey': service_key, 'Authorization': f'Bearer {service_key}'}
        self._timeout = timeout
        self._client_factory = client_factory or httpx.Client

    def _request(self, method: str, table: str, *, params: dict | None = None, json=None,
                 prefer: str | None = None) -> httpx.Response:
        headers = dict(self._headers)
        if prefer:
            headers['Prefer'] = prefer
        try:
            with self._client_factory(timeout=self._timeout) as client:
                return client.request(method, f'{self._base}/{table}', params=params, json=json, headers=headers)
        except httpx.HTTPError:
            # Không đính kèm exception gốc (có thể chứa URL/headers) vào lỗi.
            raise RepositoryError('supabase_unreachable') from None

    @staticmethod
    def _rows(response: httpx.Response) -> list[dict]:
        if response.status_code >= 300:
            raise RepositoryError(f'supabase_status_{response.status_code}')
        try:
            data = response.json()
        except ValueError:
            raise RepositoryError('supabase_bad_json') from None
        if not isinstance(data, list):
            raise RepositoryError('supabase_bad_shape')
        return data

    def find_by_request(self, owner_id, request_id):
        rows = self._rows(self._request('GET', 'analysis_runs', params={
            'select': RUN_COLUMNS, 'user_id': f'eq.{owner_id}', 'request_id': f'eq.{request_id}', 'limit': '1'}))
        return rows[0] if rows else None

    def insert_run(self, owner_id, row):
        payload = {**row, 'user_id': owner_id}
        response = self._request('POST', 'analysis_runs', params={'select': RUN_COLUMNS}, json=payload,
                                 prefer='return=representation')
        if response.status_code == 409:
            try:
                code = response.json().get('code')
            except (ValueError, AttributeError):
                code = None
            if code == '23505':
                raise DuplicateRequestError()
            raise RepositoryError(f'supabase_conflict_{code}')
        rows = self._rows(response)
        if len(rows) != 1:
            raise RepositoryError('supabase_insert_shape')
        return rows[0]

    def list_runs(self, owner_id, *, lesson_id=None, status=None, ai_status=None, limit=20, after=None):
        params = {'select': RUN_SUMMARY_COLUMNS, 'user_id': f'eq.{owner_id}',
                  'order': 'created_at.desc,id.desc', 'limit': str(limit)}
        if lesson_id is not None:
            params['lesson_id'] = f'eq.{lesson_id}'
        if status is not None:
            params['status'] = f'eq.{status}'
        if ai_status == 'not_recorded':
            params['ai_status'] = 'is.null'
        elif ai_status is not None:
            params['ai_status'] = f'eq.{ai_status}'
        if after is not None:
            created_at, run_id = after
            params['or'] = (f'(created_at.lt.{_quote(created_at)},'
                            f'and(created_at.eq.{_quote(created_at)},id.lt.{_quote(run_id)}))')
        return self._rows(self._request('GET', 'analysis_runs', params=params))

    def get_run(self, owner_id, run_id):
        if not _valid_uuid(run_id):
            return None
        rows = self._rows(self._request('GET', 'analysis_runs', params={
            'select': RUN_COLUMNS, 'id': f'eq.{run_id}', 'user_id': f'eq.{owner_id}', 'limit': '1'}))
        return rows[0] if rows else None

    def get_run_detail(self, owner_id, run_id):
        run = self.get_run(owner_id, run_id)  # kiểm sở hữu TRƯỚC khi đọc bảng con
        if run is None:
            return None
        rid = run['id']
        recs = self._rows(self._request('GET', 'recommendations', params={
            'select': RECOMMENDATION_COLUMNS, 'analysis_run_id': f'eq.{rid}', 'order': 'priority.asc,id.asc',
            'limit': str(CHILD_LIMIT)}))
        evals = self._rows(self._request('GET', 'evaluation_results', params={
            'select': EVALUATION_COLUMNS, 'analysis_run_id': f'eq.{rid}', 'order': 'id.asc',
            'limit': str(CHILD_LIMIT)}))
        reviews = self._rows(self._request('GET', 'recommendation_reviews', params={
            'select': REVIEW_COLUMNS, 'run_id': f'eq.{rid}', 'order': 'at.asc,id.asc',
            'limit': str(CHILD_LIMIT)}))
        return {'run': run, 'recommendations': recs, 'evaluations': evals, 'reviews': reviews}

    def apply_review(self, owner_id, run_id, *, recommendation_id, expected_version, decision, comment,
                     content, actor_email):
        """POST /rest/v1/rpc/review_recommendation: PostgREST chạy hàm trong một transaction."""
        if not (_valid_uuid(run_id) and _valid_uuid(recommendation_id) and _valid_uuid(owner_id)):
            return {'outcome': 'not_found'}  # tránh lỗi ép kiểu uuid (22P02) và giữ phản hồi như "không tồn tại"
        response = self._request('POST', f'rpc/{REVIEW_RPC}', json={
            'p_run_id': run_id, 'p_recommendation_id': recommendation_id, 'p_expected_version': expected_version,
            'p_decision': decision, 'p_comment': comment, 'p_content': content, 'p_actor_id': owner_id,
            'p_actor_email': actor_email})
        if response.status_code >= 300:
            raise RepositoryError(f'supabase_status_{response.status_code}')
        try:
            data = response.json()
        except ValueError:
            raise RepositoryError('supabase_bad_json') from None
        if not isinstance(data, dict) or data.get('outcome') not in REVIEW_OUTCOMES:
            raise RepositoryError('supabase_bad_shape')
        if data['outcome'] in ('ok', 'replayed') and not (isinstance(data.get('recommendation'), dict)
                                                         and isinstance(data.get('review'), dict)):
            raise RepositoryError('supabase_bad_shape')
        out = {'outcome': data['outcome']}
        if isinstance(data.get('recommendation'), dict):
            out['recommendation'] = _pick(data['recommendation'], RECOMMENDATION_FIELDS)
        if isinstance(data.get('review'), dict):
            out['review'] = _pick(data['review'], REVIEW_FIELDS)
        if (out['outcome'] == 'replayed'
                and out['review'].get('new_version') != out['recommendation'].get('version')):
            # Phòng thủ khi hàm SQL cũ còn chạy: audit khớp nhưng đã bị ghi đè -> không phải retry hợp lệ.
            return {'outcome': 'version_conflict', 'recommendation': out['recommendation']}
        return out


def get_run_repository() -> RunRepository:
    """FastAPI dependency. Thiếu cấu hình service role -> 503 (không lộ tên biến/giá trị)."""
    url = os.getenv('SUPABASE_URL', '').strip()
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '').strip()
    if not url or not key:
        raise HTTPException(503, 'Chưa cấu hình kho lưu báo cáo')
    return SupabaseRunRepository(url, key)
