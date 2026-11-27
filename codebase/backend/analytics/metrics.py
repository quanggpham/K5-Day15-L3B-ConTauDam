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


SNAPSHOT_VERSION = 2
MIN_SAMPLE = 10
TOP_N = 3

_GROUP_SQL = '''
    select lesson_id, kc_code,
           count(*) filter (where was_correct is not null) as graded,
           count(*) filter (where was_correct = false) as incorrect,
           count(*) filter (where was_correct is null) as ungraded,
           count(distinct hv) filter (where was_correct is not null) as learners
    from answers
    where lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> ''
      and kc_code is not null and trim(kc_code) <> ''
    group by lesson_id, kc_code order by lesson_id, kc_code
'''
_LESSON_SQL = '''
    select lesson_id, count(*) filter (where was_correct is not null),
           count(*) filter (where was_correct = false),
           count(*) filter (where was_correct is null),
           count(distinct hv) filter (where was_correct is not null)
    from answers
    where lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> ''
      and kc_code is not null and trim(kc_code) <> ''
    group by lesson_id
'''


def _status(graded: int) -> str:
    if graded == 0:
        return 'no_graded'
    return 'insufficient_sample' if graded < MIN_SAMPLE else 'ok'


def _rank(items: list[dict]) -> list[dict]:
    """Xếp hạng đồng hạng (1,1,3) cho nhóm status=ok; giữ trọn nhóm đồng hạng ở top N."""
    eligible = sorted((i for i in items if i['status'] == 'ok'),
                      key=lambda i: (-i['incorrect_rate'], i['kc_code']))
    ranked = []
    for index, item in enumerate(eligible):
        same = ranked and item['incorrect_rate'] == ranked[-1]['incorrect_rate']
        ranked.append({**item, 'rank': ranked[-1]['rank'] if same else index + 1})
    return [i for i in ranked if i['rank'] <= TOP_N]


def _delta_pp(current, previous):
    if current is None or previous is None:
        return None
    return round((current - previous) * 100, 2)


def build_snapshot(db, generated_at: str | None = None) -> dict:
    """Snapshot v2, không chứa mã học viên.

    {'version', 'generated_at', 'min_sample', 'catalog': [{'lesson_id','status','kc_count','sample',
       'first_event_at','last_event_at'}],
     'lessons': {lesson_id: {'lesson_id','status','sample':{'responses','learners','ungraded','incorrect'},
       'incorrect_rate','previous_lesson_id','delta_vs_previous_pp','kcs':[...],'priority':[...]}}}
    Mẫu số = lượt đầu (lan_thu=1) có was_correct; lượt chưa chấm chỉ đếm ở ungraded.
    status: ok | insufficient_sample (<10 lượt, không xếp ưu tiên) | no_graded (mẫu số 0, rate=None).
    Tên bài: dữ liệu không có nên không bịa; thời gian lấy từ events.occurred_at nếu bảng có.
    """
    from datetime import datetime, timezone
    by_lesson: dict[str, list[dict]] = {}
    for lesson, kc, graded, incorrect, ungraded, learners in db.execute(_GROUP_SQL).fetchall():
        by_lesson.setdefault(lesson, []).append({
            'kc_code': kc, 'status': _status(graded), 'graded_count': graded, 'learner_count': learners,
            'incorrect_count': incorrect, 'ungraded_count': ungraded,
            'incorrect_rate': incorrect / graded if graded else None})
    totals = {row[0]: row[1:] for row in db.execute(_LESSON_SQL).fetchall()}  # người duy nhất đếm riêng cấp bài
    try:
        times = {k: (a, b) for k, a, b in db.execute(
            'select lesson_id, min(occurred_at), max(occurred_at) from events '
            'where lesson_id is not null group by lesson_id').fetchall()}
    except Exception:  # không có bảng events: bỏ thông tin thời gian
        times = {}
    lessons, catalog = {}, []
    last_kc_rate: dict[str, float] = {}
    prev_id, prev_rate = None, None
    for lid in sorted(by_lesson):
        graded, incorrect, ungraded, learners = totals[lid]
        rate = incorrect / graded if graded else None
        kcs = [{**k, 'delta_vs_previous_pp': _delta_pp(k['incorrect_rate'], last_kc_rate.get(k['kc_code']))}
               for k in by_lesson[lid]]
        for k in kcs:
            if k['incorrect_rate'] is not None:
                last_kc_rate[k['kc_code']] = k['incorrect_rate']
        sample = {'responses': graded, 'learners': learners, 'ungraded': ungraded, 'incorrect': incorrect}
        status = _status(graded)
        lessons[lid] = {'lesson_id': lid, 'status': status, 'sample': sample, 'incorrect_rate': rate,
                        'previous_lesson_id': prev_id, 'delta_vs_previous_pp': _delta_pp(rate, prev_rate),
                        'kcs': kcs, 'priority': _rank(kcs)}
        first, last = times.get(lid, (None, None))
        catalog.append({'lesson_id': lid, 'status': status, 'kc_count': len(kcs), 'sample': sample,
                        'first_event_at': str(first) if first else None,
                        'last_event_at': str(last) if last else None})
        prev_id = lid
        if rate is not None:
            prev_rate = rate
    return {'version': SNAPSHOT_VERSION, 'generated_at': generated_at or datetime.now(timezone.utc).isoformat(),
            'min_sample': MIN_SAMPLE, 'catalog': catalog, 'lessons': lessons}
