"""Đếm lại các số bằng chứng pain từ DuckDB local (chỉ đọc). Chỉ in số tổng hợp, không in mã học viên.

Chạy: .venv/Scripts/python.exe -B evidence/count.py
Cần `data/learning_pulse.duckdb` (tạo bằng `python -m codebase.backend.analytics.ingest`).
"""
from pathlib import Path
import duckdb

DB = Path(__file__).resolve().parents[1] / 'data/learning_pulse.duckdb'
FIRST = "lan_thu = 1 and lesson_id is not null and trim(lesson_id) <> '' and kc_code is not null and trim(kc_code) <> ''"
MIN_GRADED = 10
EXAMPLES = ['ai_product_canvas', 'tool_definition_context_cost', 'react_reasoning_acting_pattern',
            'multi_agent_token_cost', 'paired_bootstrap_interpretation']


def main():
    with duckdb.connect(str(DB), read_only=True) as db:
        graded, incorrect, ungraded = db.execute(
            'select count(*) filter (where was_correct is not null), count(*) filter (where was_correct = false), '
            f'count(*) filter (where was_correct is null) from answers where {FIRST}').fetchone()
        after_first = db.execute('select count(*) from answers where lan_thu > 1').fetchone()[0]
        learners_graded, learners_all = db.execute(
            f'select count(distinct hv) filter (where {FIRST} and was_correct is not null), count(distinct hv) '
            'from answers').fetchone()
        kcs = db.execute(
            'select lesson_id, kc_code, count(*) filter (where was_correct is not null), '
            f'count(*) filter (where was_correct = false) from answers where {FIRST} group by 1, 2').fetchall()
        chats = db.execute("select count(*) from chat where starts_with(transcript, 'Day01/')").fetchone()[0]
    graded_kcs = [row for row in kcs if row[2] > 0]
    enough = sum(1 for _, _, n, _ in graded_kcs if n >= MIN_GRADED)
    print(f'Lượt lần đầu có chấm: {graded} · sai: {incorrect}/{graded} ({incorrect / graded:.2%})'
          f' · chưa chấm (loại): {ungraded} · lượt lần hai trở đi (loại): {after_first}')
    print(f'Học viên có ít nhất một lượt chấm: {learners_graded}/{learners_all} có dòng trong answers'
          f' ({learners_graded / learners_all:.2%})')
    print(f'KC có lượt chấm: {len(graded_kcs)} (trong {len(kcs)} KC có lượt lần đầu) · bài: '
          f'{len({row[0] for row in graded_kcs})} · KC có >= {MIN_GRADED} lượt chấm: '
          f'{enough}/{len(graded_kcs)} ({enough / len(graded_kcs):.2%})')
    print(f'Dòng chat có tiền tố Day01/: {chats}')
    for lesson_id, kc_code, n, wrong in sorted(kcs, key=lambda row: row[1]):
        if kc_code in EXAMPLES:
            print(f'  ví dụ {lesson_id} · {kc_code}: {wrong}/{n} sai ({wrong / n:.2%})')


if __name__ == '__main__':
    main()
