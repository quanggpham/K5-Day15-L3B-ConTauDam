"""Shared evidence-only report until approved lesson sources are available."""
import re

_DAY = re.compile(r'day\s*0*([1-9][0-9]?)(?!\d)', re.IGNORECASE)


def resolve_lesson_ids(value: str, snapshot: dict) -> list[str]:
    """Mọi bài được nhắc tới trong câu hỏi, theo thứ tự xuất hiện, không trùng.

    Nhận mã bài đầy đủ nằm trong câu, hoặc bí danh `Day NN` / `DayNN`.
    Bí danh khớp nhiều bài (mơ hồ) thì bỏ qua bài đó.
    """
    hits = [(value.find(key), key) for key in snapshot if key in value]
    for match in _DAY.finditer(value):
        prefix = f"program-day{int(match.group(1)):02d}:"
        matches = [key for key in snapshot if key.casefold().startswith(prefix)]
        if len(matches) == 1:
            hits.append((match.start(), matches[0]))
    return list(dict.fromkeys(key for _, key in sorted(hits)))


def resolve_lesson_id(value: str, snapshot: dict) -> str | None:
    ids = resolve_lesson_ids(value, snapshot)
    return ids[0] if ids else None


def create_report(lesson_id: str, snapshot: dict) -> dict | None:
    metrics = snapshot.get(lesson_id)
    if metrics is None:
        return None
    priority = sorted((row for row in metrics if not row.get('insufficient_data') and row.get('incorrect_rate') is not None and row['incorrect_rate'] > 0),
                      key=lambda row: (-row['incorrect_rate'], row['kc_code']))
    ranked = []
    for index, row in enumerate(priority):
        rank = ranked[-1]['rank'] if ranked and row['incorrect_rate'] == ranked[-1]['incorrect_rate'] else index + 1
        ranked.append({**row, 'rank': rank})
    return {'lesson_id': lesson_id, 'metrics': metrics, 'priority': ranked,
            'notice': 'Chưa có căn cứ bài giảng; chưa tạo đề xuất AI. Ngưỡng ưu tiên: ít nhất 10 lượt được chấm; nhóm ít lượt chỉ dùng tham khảo.'}
