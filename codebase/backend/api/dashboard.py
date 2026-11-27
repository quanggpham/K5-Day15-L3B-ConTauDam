"""GET /api/dashboard: catalog và chỉ số bài đang xem từ snapshot v2 (không tạo số 0 khi thiếu dữ liệu)."""
from fastapi import APIRouter, Depends, HTTPException
from codebase.backend.analytics.snapshot import read_snapshot_v2
from codebase.backend.security.auth import require_coach

router = APIRouter()

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


def _lesson_view(lesson: dict) -> dict:
    sample = lesson.get('sample') or {}
    responses, incorrect = sample.get('responses', 0), sample.get('incorrect', 0)
    rate = lesson.get('incorrect_rate')
    kcs = lesson.get('kcs') or []
    return {
        'lesson_id': lesson['lesson_id'], 'status': lesson.get('status'), 'sample': sample,
        'incorrect_rate': rate,
        'first_attempt_accuracy': None if rate is None else round(1 - rate, 6),
        'delta_vs_previous_pp': lesson.get('delta_vs_previous_pp'),
        'previous_lesson_id': lesson.get('previous_lesson_id'),
        'sufficient_kc_count': sum(1 for k in kcs if k.get('status') == 'ok'),
        'kc_count': len(kcs), 'kcs': kcs, 'priority': lesson.get('priority') or [],
        'distribution': {'correct': responses - incorrect, 'incorrect': incorrect,
                         'ungraded': sample.get('ungraded', 0)},
    }


@router.get('/api/dashboard')
def dashboard(lesson_id: str | None = None, user: dict = Depends(require_coach)):
    snapshot = read_snapshot_v2()
    catalog = snapshot['catalog'] if snapshot else []
    if not catalog:
        return {'status': 'no_data'}
    ids = [c['lesson_id'] for c in catalog]
    selected = lesson_id or ids[-1]  # catalog đã sắp theo thứ tự bài; cuối = mới nhất
    lesson = snapshot['lessons'].get(selected) if selected in ids else None
    if lesson is None:
        raise HTTPException(404, 'Không có dữ liệu cho bài học')
    return {'status': 'ok', 'generated_at': snapshot.get('generated_at'),
            'min_sample': snapshot.get('min_sample'), 'units': UNITS,
            'catalog': catalog, 'selected_lesson_id': selected, 'lesson': _lesson_view(lesson)}
