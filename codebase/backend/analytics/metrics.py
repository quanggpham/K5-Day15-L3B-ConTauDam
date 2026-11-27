"""Tổng hợp số liệu theo bài; không trả dữ liệu từng học viên."""


def lesson_metrics(db, lesson_id: str) -> list[dict]:
    rows = db.execute('''
        select kc_code,
               count(*) filter (where was_correct is not null) as graded_count,
               count(*) filter (where was_correct = false) as incorrect_count,
               count(*) filter (where was_correct is null) as ungraded_count
        from answers
        where lesson_id = ? and lan_thu = 1 and kc_code is not null and trim(kc_code) <> ''
        group by kc_code order by kc_code
    ''', [lesson_id]).fetchall()
    return [dict(kc_code=kc, graded_count=graded, incorrect_count=incorrect,
                 ungraded_count=ungraded, incorrect_rate=incorrect / graded if graded else None)
            for kc, graded, incorrect, ungraded in rows]


def export_snapshot(db) -> dict:
    """Xuất số liệu tổng hợp, gắn cờ mẫu nhỏ và không xuất mã học viên."""
    groups = db.execute('''
        select lesson_id, kc_code,
               count(*) filter (where was_correct is not null) as graded,
               count(*) filter (where was_correct = false) as incorrect,
               count(*) filter (where was_correct is null) as ungraded
        from answers
        where lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> ''
          and kc_code is not null and trim(kc_code) <> ''
        group by lesson_id, kc_code order by lesson_id, kc_code
    ''').fetchall()
    result = {}
    for lesson, kc, graded, incorrect, ungraded in groups:
        item = {'kc_code': kc, 'graded_count': graded, 'incorrect_count': incorrect,
                'ungraded_count': ungraded, 'incorrect_rate': incorrect / graded if graded else None}
        if graded < 10:
            item['insufficient_data'] = True
        result.setdefault(lesson, []).append(item)
    return result
