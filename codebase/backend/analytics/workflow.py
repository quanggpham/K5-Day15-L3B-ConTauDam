"""Shared evidence-only report until approved lesson sources are available."""


def create_report(lesson_id: str, snapshot: dict) -> dict | None:
    metrics = snapshot.get(lesson_id)
    if metrics is None:
        return None
    priority = sorted((row for row in metrics if not row.get('insufficient_data') and row.get('incorrect_rate') is not None),
                      key=lambda row: (-row['incorrect_rate'], row['kc_code']))
    return {'lesson_id': lesson_id, 'metrics': metrics, 'priority': priority,
            'notice': 'Chưa có căn cứ bài giảng; chưa tạo đề xuất AI. Ngưỡng ưu tiên: ít nhất 10 lượt được chấm; nhóm dưới 5 học viên được ẩn số liệu.'}
