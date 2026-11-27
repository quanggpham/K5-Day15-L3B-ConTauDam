"""Hình dạng "LessonView" dùng chung cho GET /api/dashboard và metrics_snapshot của analysis run.

Hợp đồng với frontend (`features/dashboard/types.ts` LessonView, `features/reports/snapshot.ts` isLessonView):
LESSON_VIEW_KEYS phải có đủ; isLessonView yêu cầu `sample`, `distribution` là object, `kcs`, `priority` là mảng.
Chỉ suy ra bằng phép tính trên chính bài đã cho (không đọc dữ liệu khác). Thiếu số đầu vào -> None, không điền 0.
Hàm idempotent: lesson_view(lesson_view(x)) == lesson_view(x) (nên đọc lại snapshot đã lưu kiểu nào cũng được).
"""
from __future__ import annotations

UNITS = {
    'responses': 'lượt (lượt trả lời đầu tiên đã chấm)',
    'learners': 'người (học viên duy nhất có lượt chấm)',
    'ungraded': 'lượt (chưa chấm, không tính vào mẫu số)',
    'incorrect': 'lượt',
    'correct': 'lượt',
    'incorrect_rate': 'tỷ lệ 0-1 trên lượt',
    'first_attempt_accuracy': 'tỷ lệ 0-1 trên lượt',
    'delta_vs_previous_pp': 'điểm phần trăm của tỷ lệ sai so với bài trước',
}

LESSON_VIEW_KEYS = ('lesson_id', 'status', 'sample', 'incorrect_rate', 'first_attempt_accuracy',
                    'delta_vs_previous_pp', 'previous_lesson_id', 'sufficient_kc_count', 'kc_count', 'kcs',
                    'priority', 'distribution')


def _count(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _distribution(sample: dict) -> dict | None:
    """correct = responses - incorrect; chỉ khi cả ba số đều có thật (không mặc định 0)."""
    responses, incorrect, ungraded = (_count(sample.get(k)) for k in ('responses', 'incorrect', 'ungraded'))
    if responses is None or incorrect is None or ungraded is None or incorrect > responses:
        return None
    return {'correct': responses - incorrect, 'incorrect': incorrect, 'ungraded': ungraded}


def lesson_view(lesson: dict) -> dict:
    sample = lesson.get('sample') if isinstance(lesson.get('sample'), dict) else {}
    rate = lesson.get('incorrect_rate')
    kcs = lesson.get('kcs') if isinstance(lesson.get('kcs'), list) else []
    priority = lesson.get('priority') if isinstance(lesson.get('priority'), list) else []
    has_rate = isinstance(rate, (int, float)) and not isinstance(rate, bool)
    return {
        'lesson_id': lesson.get('lesson_id'), 'status': lesson.get('status'), 'sample': sample,
        'incorrect_rate': rate,
        'first_attempt_accuracy': round(1 - rate, 6) if has_rate else None,
        'delta_vs_previous_pp': lesson.get('delta_vs_previous_pp'),
        'previous_lesson_id': lesson.get('previous_lesson_id'),
        'sufficient_kc_count': sum(1 for k in kcs if isinstance(k, dict) and k.get('status') == 'ok'),
        'kc_count': len(kcs), 'kcs': kcs, 'priority': priority,
        'distribution': _distribution(sample),
    }
