"""Tạo snapshot tổng hợp local; không chứa mã học viên."""
import json
from pathlib import Path
import duckdb
from codebase.backend.analytics.metrics import export_snapshot, build_snapshot


def extra_counts(db) -> dict:
    """Số đếm phụ trợ cho CLI. Chỉ đếm, không đọc nội dung chat hay mã học viên."""
    chat = db.execute("select regexp_extract(transcript, '^(Day[0-9]+)/', 1) as day, count(*) "
                      "from chat where transcript is not null group by 1").fetchall()
    return {'chat_lines_by_day': {day.casefold(): count for day, count in chat if day},
            'answer_rows': db.execute('select count(*) from answers').fetchone()[0],
            'attempts_after_first': db.execute('select count(*) from answers where lan_thu > 1').fetchone()[0]}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[3]
    with duckdb.connect(str(root / 'data/learning_pulse.duckdb'), read_only=True) as db:
        snapshot = export_snapshot(db)
        snapshot_v2 = build_snapshot(db)
        extra = extra_counts(db)
    destination = root / 'data/aggregate.json'
    destination.write_text(json.dumps(snapshot, ensure_ascii=False), encoding='utf-8')
    print(f'Created snapshot with {len(snapshot)} lessons at {destination}')
    (root / 'data/aggregate.v2.json').write_text(json.dumps(snapshot_v2, ensure_ascii=False), encoding='utf-8')
    (root / 'data/extra_counts.json').write_text(json.dumps(extra, ensure_ascii=False), encoding='utf-8')
