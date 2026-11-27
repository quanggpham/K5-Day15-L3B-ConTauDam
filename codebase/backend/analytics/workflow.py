"""Shared evidence-only report until approved lesson sources are available."""
import re


def resolve_lesson_id(value: str, snapshot: dict) -> str | None:
    if value in snapshot:
        return value
    match = re.fullmatch(r'day\s*0*([1-9][0-9]?)', value, re.IGNORECASE)
    if not match:
        return None
    prefix = f"program-day{int(match.group(1)):02d}:"
    matches = [key for key in snapshot if key.casefold().startswith(prefix)]
    return matches[0] if len(matches) == 1 else None


def create_report(lesson_id: str, snapshot: dict) -> dict | None:
    metrics = snapshot.get(lesson_id)
    if metrics is None:
        return None
    priority = sorted((row for row in metrics if not row.get('insufficient_data') and row.get('incorrect_rate') is not None),
                      key=lambda row: (-row['incorrect_rate'], row['kc_code']))
    ranked = []
    for index, row in enumerate(priority):
        rank = ranked[-1]['rank'] if ranked and row['incorrect_rate'] == ranked[-1]['incorrect_rate'] else index + 1
        ranked.append({**row, 'rank': rank})
    return {'lesson_id': lesson_id, 'metrics': metrics, 'priority': ranked,
            'notice': 'Chưa có căn cứ bài giảng; chưa tạo đề xuất AI. Ngưỡng ưu tiên: ít nhất 10 lượt được chấm; nhóm ít lượt chỉ dùng tham khảo.'}
