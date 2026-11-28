"""Công cụ của bài toán. Mỗi hàm có @tool; docstring ghi: tên · input · output · có tác động ra ngoài không.

Mọi công cụ chỉ đọc số liệu đã tổng hợp (snapshot JSON), không đọc dữ liệu từng học viên.
"""
import json
import os

from tracing import tool
from backend.analytics.snapshot import read_snapshot
from backend.analytics.workflow import create_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRA_COUNTS_PATH = os.path.join(ROOT, 'data', 'extra_counts.json')


def _totals(metrics: list[dict]) -> tuple[int, int, int]:
    return (sum(m.get('graded_count') or 0 for m in metrics),
            sum(m.get('incorrect_count') or 0 for m in metrics),
            sum(m.get('ungraded_count') or 0 for m in metrics))


@tool
def lesson_report(lesson_id: str) -> dict | None:
    """Báo cáo bài học. Input: mã bài; output: {"lesson_id", "metrics", "priority", "notice"} hoặc None.
    Không tác động ra ngoài."""
    return create_report(lesson_id, read_snapshot())


@tool
def lesson_comparison(lesson_ids: list[str]) -> dict | None:
    """So sánh các bài. Input: danh sách mã bài; output: {"lessons": [{"lesson_id", "graded_count",
    "incorrect_count", "ungraded_count", "incorrect_rate"}], "delta_pp": {bài A: {bài B: tỷ lệ sai A trừ B,
    điểm %}}} hoặc None nếu có bài không tồn tại. Không tác động ra ngoài."""
    snapshot = read_snapshot()
    rows = []
    for lesson_id in dict.fromkeys(lesson_ids):
        if lesson_id not in snapshot:
            return None
        graded, incorrect, ungraded = _totals(snapshot[lesson_id])
        rows.append({'lesson_id': lesson_id, 'graded_count': graded, 'incorrect_count': incorrect,
                     'ungraded_count': ungraded, 'incorrect_rate': incorrect / graded if graded else None})
    delta = {a['lesson_id']: {b['lesson_id']: round((a['incorrect_rate'] - b['incorrect_rate']) * 100, 2)
                              for b in rows
                              if a is not b and a['incorrect_rate'] is not None and b['incorrect_rate'] is not None}
             for a in rows}
    return {'lessons': rows, 'delta_pp': delta}


@tool
def dataset_summary() -> dict:
    """Tổng toàn bộ dữ liệu. Input: không có; output: {"lessons", "graded_count", "incorrect_count",
    "correct_count", "ungraded_count", "incorrect_rate", "correct_rate"}. Mẫu số là lượt lần đầu có chấm
    đúng/sai, không phải số học viên. Không tác động ra ngoài."""
    snapshot = read_snapshot()
    graded, incorrect, ungraded = _totals([m for metrics in snapshot.values() for m in metrics])
    correct = graded - incorrect
    return {'lessons': sorted(snapshot), 'graded_count': graded, 'incorrect_count': incorrect,
            'correct_count': correct, 'ungraded_count': ungraded,
            'incorrect_rate': incorrect / graded if graded else None,
            'correct_rate': correct / graded if graded else None}


@tool
def dataset_extra() -> dict:
    """Số đếm phụ trợ toàn dữ liệu (số dòng chat theo bài, số lượt trả lời). Input: không có;
    output: dict hoặc {} nếu chưa xuất. Chỉ số đếm, không có nội dung chat. Không tác động ra ngoài."""
    try:
        with open(EXTRA_COUNTS_PATH, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
