"""POST /api/analysis-runs/{id}/copilot: 4 thao tác cố định, CHỈ dựa trên snapshot đã lưu của run.

- explain_priority, compare_previous: câu trả lời dựng bằng code từ `metrics_snapshot` đã lưu lúc tạo run
  (không đọc snapshot hiện tại, không gọi LLM, không gửi gì lên model/Langfuse, không tính số mới ngoài đổi
  tỷ lệ 0-1 sang %). Kèm `evidence` = danh sách (kc_code, field, value) đã dùng.
- review_plan_15m, recheck_questions: cần Lesson KB + hiệu chuẩn JEV. `ai_gate(run)` kiểm tại server;
  hiện luôn đóng -> 409 code=ai_unavailable kèm `reasons` ổn định; không tạo nội dung.

kc_code: bắt buộc với explain_priority/recheck_questions; tuỳ chọn với compare_previous/review_plan_15m;
nếu có thì phải thuộc `lesson.kcs` của snapshot đã lưu, không thì 422.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from codebase.backend.api.analysis_runs import RUN_SNAPSHOT_SCHEMA, _unavailable
from codebase.backend.api.run_repository import RepositoryError, RunRepository, get_run_repository
from codebase.backend.security.auth import require_coach

router = APIRouter()

Action = Literal['explain_priority', 'compare_previous', 'review_plan_15m', 'recheck_questions']
KC_REQUIRED = frozenset({'explain_priority', 'recheck_questions'})
AI_ACTIONS = frozenset({'review_plan_15m', 'recheck_questions'})
# Cấu hình mở AI (đường dẫn tới tài liệu đã duyệt). Chưa có -> gate đóng.
KB_ENV = 'LESSON_KB_PATH'
JEV_ENV = 'JEV_CALIBRATION_PATH'
# Chưa có pipeline sinh nội dung đã nghiệm thu: kể cả khi đủ KB/JEV, gate vẫn đóng (fail-closed).
AI_GENERATION_ENABLED = False
_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
SOURCE = 'stored_snapshot'


class CopilotBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Action
    kc_code: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator('kc_code')
    @classmethod
    def _kc_ok(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or _CONTROL.search(value)):
            raise ValueError('không được rỗng hoặc chứa ký tự điều khiển')
        return value


@dataclass(frozen=True)
class AiGate:
    open: bool
    reasons: tuple[str, ...]


def ai_gate(run: dict, env: Mapping[str, str] | None = None) -> AiGate:
    """Điều kiện mở AI tại server. Lý do (ổn định): kb_missing, jev_uncalibrated, run_ai_not_ready,
    generation_not_enabled. Đóng nếu có bất kỳ lý do nào."""
    env = os.environ if env is None else env
    reasons = []
    for key, reason in ((KB_ENV, 'kb_missing'), (JEV_ENV, 'jev_uncalibrated')):
        path = (env.get(key) or '').strip()
        if not path or not Path(path).is_file():
            reasons.append(reason)
    if run.get('ai_status') != 'ready':
        reasons.append('run_ai_not_ready')
    if not AI_GENERATION_ENABLED:
        reasons.append('generation_not_enabled')
    return AiGate(open=not reasons, reasons=tuple(reasons))


def _err(status: int, code: str, message: str, **extra) -> HTTPException:
    return HTTPException(status, {'code': code, 'message': message, **extra})


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _pct(rate) -> str:
    return f'{rate * 100:.1f}%'


def _stored_lesson(run: dict) -> tuple[dict, dict]:
    stored = run.get('metrics_snapshot')
    if not (isinstance(stored, dict) and stored.get('schema') == RUN_SNAPSHOT_SCHEMA
            and isinstance(stored.get('lesson'), dict)):
        raise _err(422, 'snapshot_unavailable',
                   'Báo cáo không có snapshot số liệu định dạng hiện hành nên Copilot không có căn cứ.')
    return stored, stored['lesson']


def _kcs(lesson: dict) -> dict[str, dict]:
    return {k['kc_code']: k for k in lesson.get('kcs') or []
            if isinstance(k, dict) and isinstance(k.get('kc_code'), str)}


class _Evidence:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, kc_code, field: str, value):
        """Chỉ ghi căn cứ thật sự có trong snapshot (value None -> không ghi)."""
        if value is not None:
            self.items.append({'kc_code': kc_code, 'field': field, 'value': value})
        return value


def explain_priority(stored: dict, lesson: dict, kc_code: str) -> tuple[str, str, list[dict]]:
    ev = _Evidence()
    kc = _kcs(lesson)[kc_code]
    status = ev.add(kc_code, 'kcs.status', kc.get('status'))
    graded = kc.get('graded_count')
    rate = kc.get('incorrect_rate')
    learners = kc.get('learner_count')
    priority = [p for p in lesson.get('priority') or [] if isinstance(p, dict) and isinstance(p.get('rank'), int)]
    entry = next((p for p in priority if p.get('kc_code') == kc_code), None)
    if status == 'no_graded':
        ev.add(kc_code, 'kcs.graded_count', graded)
        ev.add(kc_code, 'kcs.ungraded_count', kc.get('ungraded_count'))
        return 'ok', (f'KC {kc_code} không có lượt chấm lần đầu (mẫu số 0) nên không có tỷ lệ sai '
                      'và không được xếp ưu tiên.'), ev.items
    if status == 'insufficient_sample':
        ev.add(kc_code, 'kcs.graded_count', graded)
        min_sample = ev.add(None, 'min_sample', stored.get('min_sample'))
        text = f'KC {kc_code} chỉ có {graded} lượt chấm lần đầu'
        text += f', dưới ngưỡng {min_sample} lượt' if min_sample is not None else ', dưới ngưỡng mẫu tối thiểu'
        text += ' nên chỉ hiển thị số tổng hợp, không xếp ưu tiên.'
        if _is_num(ev.add(kc_code, 'kcs.incorrect_rate', rate)):
            text += f' Tỷ lệ sai ghi nhận: {_pct(rate)} (mẫu nhỏ, chưa đủ tin cậy).'
        return 'ok', text, ev.items
    if status != 'ok' or not _is_num(rate):
        return 'ok', f'KC {kc_code} có trạng thái số liệu "{status}" nên không được xếp ưu tiên.', ev.items
    ev.add(kc_code, 'kcs.incorrect_rate', rate)
    ev.add(kc_code, 'kcs.graded_count', graded)
    ev.add(kc_code, 'kcs.learner_count', learners)
    base = f'tỷ lệ sai {_pct(rate)} trên {graded} lượt chấm lần đầu'
    if learners is not None:
        base += f' ({learners} người)'
    if entry is not None:
        rank = ev.add(kc_code, 'priority.rank', entry['rank'])
        text = f'KC {kc_code} đứng hạng {rank} trong nhóm ưu tiên đã lưu: {base}.'
        tied = [p for p in priority if p['rank'] == rank and p.get('kc_code') != kc_code]
        for p in tied:
            ev.add(p.get('kc_code'), 'priority.rank', p['rank'])
            ev.add(p.get('kc_code'), 'priority.incorrect_rate', p.get('incorrect_rate'))
        if tied:
            text += ' Đồng hạng (cùng tỷ lệ sai) với: ' + ', '.join(str(p.get('kc_code')) for p in tied) + '.'
        return 'ok', text, ev.items
    ranked = [p for p in priority if _is_num(p.get('incorrect_rate'))]
    if not ranked:
        return 'ok', f'KC {kc_code} đủ mẫu ({base}) nhưng nhóm ưu tiên đã lưu đang rỗng.', ev.items
    lowest = min(ranked, key=lambda p: (p['incorrect_rate'], str(p.get('kc_code'))))
    ev.add(lowest.get('kc_code'), 'priority.rank', lowest['rank'])
    ev.add(lowest.get('kc_code'), 'priority.incorrect_rate', lowest['incorrect_rate'])
    return 'ok', (f'KC {kc_code} đủ mẫu ({base}) nhưng nằm ngoài nhóm ưu tiên đã lưu; mức thấp nhất trong nhóm '
                  f'là {_pct(lowest["incorrect_rate"])} (KC {lowest.get("kc_code")}, hạng {lowest["rank"]}).'), ev.items


def _direction(delta) -> str:
    if delta > 0:
        return f'tăng {delta} điểm phần trăm'
    if delta < 0:
        return f'giảm {-delta} điểm phần trăm'
    return 'không đổi'


def compare_previous(lesson: dict, kc_code: str | None) -> tuple[str, str, list[dict]]:
    ev = _Evidence()
    lesson_id = lesson.get('lesson_id')
    previous = ev.add(None, 'previous_lesson_id', lesson.get('previous_lesson_id'))
    if previous is None:
        return 'insufficient_comparison_data', 'Snapshot đã lưu không có bài trước để so sánh.', ev.items
    if kc_code is None:
        delta = lesson.get('delta_vs_previous_pp')
        rate = lesson.get('incorrect_rate')
        if not (_is_num(delta) and _is_num(rate)):
            return ('insufficient_comparison_data',
                    f'Snapshot đã lưu không có chênh lệch tỷ lệ sai giữa bài {lesson_id} và bài trước {previous}.',
                    ev.items)
        ev.add(None, 'incorrect_rate', rate)
        ev.add(None, 'delta_vs_previous_pp', delta)
        responses = ev.add(None, 'sample.responses', (lesson.get('sample') or {}).get('responses'))
        sample = f' trên {responses} lượt chấm lần đầu' if responses is not None else ''
        return 'ok', (f'Tỷ lệ sai của bài {lesson_id} là {_pct(rate)}{sample}; {_direction(delta)} '
                      f'so với bài trước {previous}.'), ev.items
    kc = _kcs(lesson)[kc_code]
    delta = kc.get('delta_vs_previous_pp')
    rate = kc.get('incorrect_rate')
    if not (_is_num(delta) and _is_num(rate)):
        return ('insufficient_comparison_data',
                f'Snapshot đã lưu không có số liệu so sánh của KC {kc_code} với bài trước.', ev.items)
    ev.add(kc_code, 'kcs.incorrect_rate', rate)
    ev.add(kc_code, 'kcs.delta_vs_previous_pp', delta)
    ev.add(kc_code, 'kcs.graded_count', kc.get('graded_count'))
    ev.add(kc_code, 'kcs.status', kc.get('status'))
    note = ' (mẫu dưới ngưỡng, chỉ tham khảo)' if kc.get('status') != 'ok' else ''
    return 'ok', (f'Tỷ lệ sai của KC {kc_code} ở bài {lesson_id} là {_pct(rate)}; {_direction(delta)} so với lần '
                  f'gần nhất trước đó KC này có số liệu{note}.'), ev.items


def run_copilot(run: dict, body: CopilotBody, env: Mapping[str, str] | None = None) -> dict:
    stored, lesson = _stored_lesson(run)
    kcs = _kcs(lesson)
    if body.action in KC_REQUIRED and body.kc_code is None:
        raise _err(422, 'kc_required', 'Thao tác này cần chọn một KC.')
    if body.kc_code is not None and body.kc_code not in kcs:
        raise _err(422, 'kc_not_in_snapshot', 'KC không có trong snapshot đã lưu của báo cáo.')
    if body.action in AI_ACTIONS:
        gate = ai_gate(run, env)
        if not gate.open:
            raise _err(409, 'ai_unavailable', 'Chưa đủ điều kiện mở AI (cần Lesson KB được phép và hiệu chuẩn JEV).',
                       reasons=list(gate.reasons))
        raise _err(409, 'ai_unavailable', 'Chưa có pipeline sinh nội dung.', reasons=['generation_not_enabled'])
    if body.action == 'explain_priority':
        status, message, evidence = explain_priority(stored, lesson, body.kc_code)
    else:
        status, message, evidence = compare_previous(lesson, body.kc_code)
    return {'run_id': run['id'], 'action': body.action, 'kc_code': body.kc_code, 'status': status,
            'message': message, 'evidence': evidence, 'source': SOURCE, 'generated_by': 'code',
            'snapshot_version': stored.get('snapshot_version') or run.get('snapshot_version'),
            'units': {'incorrect_rate': 'tỷ lệ 0-1 trên lượt', 'delta_vs_previous_pp': 'điểm phần trăm',
                      'graded_count': 'lượt', 'learner_count': 'người'}}


@router.post('/api/analysis-runs/{run_id}/copilot')
def post_copilot(run_id: str, body: CopilotBody, user: dict = Depends(require_coach),
                 repo: RunRepository = Depends(get_run_repository)):
    try:
        run = repo.get_run(user['id'], run_id)
    except RepositoryError:
        raise _unavailable() from None
    if run is None:
        raise HTTPException(404, 'Không tìm thấy báo cáo')
    return run_copilot(run, body)
