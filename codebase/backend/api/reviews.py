"""POST /api/analysis-runs/{id}/reviews: duyệt một đề xuất với optimistic locking theo `version`.

Luồng: require_coach (401/403) -> kiểm owner của run (404 như nhau khi không tồn tại/không thuộc coach)
-> repo.apply_review: MỘT transaction cập nhật đề xuất + bump version + ghi audit (người thao tác từ session,
trạng thái/nội dung trước và sau, thời điểm). Không nhận actor/owner từ client (extra='forbid').

Máy trạng thái (review_status NULL coi như 'pending'), định nghĩa ở run_repository.REVIEW_TRANSITIONS và
lặp lại trong hàm SQL public.review_recommendation:
  pending           -> accept | reject | request_changes
  accepted          -> reject | request_changes            (coach đổi ý)
  rejected          -> accept | request_changes
  changes_requested -> edited | reject                     (sau yêu cầu sửa CHỈ sửa tay hoặc bỏ đề xuất)
  edited            -> accept | reject | request_changes | edited   (duyệt lại bản sửa tay / sửa tiếp)
Bản `edited`: thay content, is_edited=true, needs_rereview=true, jev_score=null (không thừa hưởng JEV).
needs_rereview giữ true sau khi đã sửa (= bản sửa chưa được kiểm định lại); duyệt lại của coach nằm ở
review_status.

Mã phản hồi: 201 ghi mới; 200 + replayed=true khi gửi lại đúng request đã thành công (retry sau timeout) VÀ
lần ghi đó vẫn là trạng thái hiện tại (audit.new_version == version hiện tại; đã bị quyết định khác ghi đè -> 409);
404 run/đề xuất không thấy; 409 version_conflict (payload có bản hiện tại để UI tải lại); 422 invalid_transition
hoặc body sai; 503 kho lỗi.
"""
from __future__ import annotations

import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from codebase.backend.api.analysis_runs import _recommendation_view, _review_view, _unavailable
from codebase.backend.api.run_repository import REVIEW_TRANSITIONS, RepositoryError, RunRepository, get_run_repository
from codebase.backend.security.auth import require_coach

router = APIRouter()

MAX_COMMENT = 2000
MAX_CONTENT = 4000
_ID_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
_TEXT_CONTROL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')  # cho phép \t \n \r trong văn bản nhiều dòng


class ReviewBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    recommendation_id: str = Field(min_length=1, max_length=64)
    version: int = Field(ge=1, le=2_147_483_647, description='Phiên bản đề xuất mà UI đang hiển thị')
    decision: Literal['accept', 'reject', 'request_changes', 'edited']
    comment: str | None = Field(default=None, max_length=MAX_COMMENT)
    content: str | None = Field(default=None, max_length=MAX_CONTENT)

    @field_validator('recommendation_id')
    @classmethod
    def _id_ok(cls, value: str) -> str:
        if not value.strip() or _ID_CONTROL.search(value):
            raise ValueError('không được rỗng hoặc chứa ký tự điều khiển')
        return value

    @field_validator('comment', 'content')
    @classmethod
    def _text_ok(cls, value: str | None) -> str | None:
        if value is not None and _TEXT_CONTROL.search(value):
            raise ValueError('chứa ký tự điều khiển')
        return value

    @model_validator(mode='after')
    def _content_rules(self):
        if self.comment is not None and not self.comment.strip():
            self.comment = None  # nhận xét rỗng = không có nhận xét (giữ so khớp replay ổn định)
        if self.decision == 'edited':
            if self.content is None or not self.content.strip():
                raise ValueError('content bắt buộc khi decision=edited')
        elif self.content is not None:
            raise ValueError('content chỉ dùng khi decision=edited')
        return self


def submit_review(repo: RunRepository, user: dict, run_id: str, body: ReviewBody) -> tuple[dict, bool]:
    """Trả (payload, replayed). Raise HTTPException 404/409/422/503."""
    try:
        if repo.get_run(user['id'], run_id) is None:
            raise HTTPException(404, 'Không tìm thấy báo cáo')
        result = repo.apply_review(user['id'], run_id, recommendation_id=body.recommendation_id,
                                   expected_version=body.version, decision=body.decision, comment=body.comment,
                                   content=body.content, actor_email=user.get('email'))
    except RepositoryError:
        raise _unavailable() from None
    outcome = result['outcome']
    if outcome == 'not_found':
        raise HTTPException(404, 'Không tìm thấy đề xuất trong báo cáo này')
    current = result.get('recommendation')
    if outcome == 'version_conflict':
        raise HTTPException(409, {
            'code': 'version_conflict',
            'message': 'Đề xuất đã được cập nhật ở nơi khác. Tải lại báo cáo trước khi lưu tiếp.',
            'recommendation_id': body.recommendation_id, 'expected_version': body.version,
            'current_version': current.get('version') if current else None,
            'recommendation': _recommendation_view(current) if current else None,
            'reload_url': f'/api/analysis-runs/{run_id}'})
    if outcome == 'invalid_transition':
        status = (current or {}).get('review_status') or 'pending'
        raise HTTPException(422, {
            'code': 'invalid_transition', 'message': 'Quyết định này không hợp lệ ở trạng thái hiện tại.',
            'review_status': status, 'allowed_decisions': list(REVIEW_TRANSITIONS.get(status, ()))})
    if outcome == 'invalid_input':
        raise HTTPException(422, {'code': 'invalid_input', 'message': 'Dữ liệu duyệt không hợp lệ.'})
    return ({'recommendation': _recommendation_view(result['recommendation']),
             'review': _review_view(result['review']), 'replayed': outcome == 'replayed'},
            outcome == 'replayed')


@router.post('/api/analysis-runs/{run_id}/reviews', status_code=201)
def post_review(run_id: str, body: ReviewBody, response: Response, user: dict = Depends(require_coach),
                repo: RunRepository = Depends(get_run_repository)):
    payload, replayed = submit_review(repo, user, run_id, body)
    if replayed:
        response.status_code = 200
    return payload
