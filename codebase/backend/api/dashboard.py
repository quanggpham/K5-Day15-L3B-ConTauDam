"""GET /api/dashboard: catalog và chỉ số bài đang xem từ snapshot v2 (không tạo số 0 khi thiếu dữ liệu)."""
from fastapi import APIRouter, Depends, HTTPException
from codebase.backend.analytics.snapshot import read_snapshot_v2
from codebase.backend.api.lesson_view import UNITS, lesson_view
from codebase.backend.security.auth import require_coach

router = APIRouter()


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
            'catalog': catalog, 'selected_lesson_id': selected, 'lesson': lesson_view(lesson)}
