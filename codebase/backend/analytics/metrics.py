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


def export_snapshot(db, minimum_learners: int = 5) -> dict:
    """Chỉ đưa số liệu nhóm đủ mẫu vào bản tổng hợp; không xuất mã học viên."""
    if minimum_learners < 5:
        raise ValueError('Ngưỡng tối thiểu là 5 học viên')
    groups = db.execute('''
        select lesson_id, kc_code, count(distinct hv) filter (where was_correct is not null) as learners,
               count(*) filter (where was_correct is not null) as graded,
               count(*) filter (where was_correct = false) as incorrect,
               count(*) filter (where was_correct is null) as ungraded
        from answers
        where lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> ''
          and kc_code is not null and trim(kc_code) <> ''
        group by lesson_id, kc_code order by lesson_id, kc_code
    ''').fetchall()
    result = {}
    for lesson, kc, learners, graded, incorrect, ungraded in groups:
        if learners < minimum_learners:
            item = {'kc_code': kc, 'insufficient_data': True}
        else:
            item = {'kc_code': kc, 'graded_count': graded, 'incorrect_count': incorrect,
                    'ungraded_count': ungraded, 'incorrect_rate': incorrect / graded if graded else None}
        result.setdefault(lesson, []).append(item)
    return result
