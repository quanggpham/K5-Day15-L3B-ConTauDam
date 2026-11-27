"""CLI và dashboard dùng chung báo cáo theo mã bài học."""
import json
from fastapi import HTTPException
from tools import lesson_report
from backend.security.input_guard import refusal
from tracing import note


def answer(text: str) -> dict:
    denied = refusal(text)
    if denied:
        note("Từ chối yêu cầu ngoài phạm vi")
        return {"output": denied}
    try:
        result = lesson_report(text.strip())
    except HTTPException:
        note('Không có snapshot tổng hợp')
        return {'output': 'Chưa có dữ liệu tổng hợp. Vui lòng chuẩn bị snapshot trước.'}
    if result is None:
        note('Đầu vào không phải mã bài học có trong dữ liệu')
        return {'output': 'Vui lòng chỉ cung cấp mã bài học có trong dữ liệu. Không hỗ trợ truy vấn dữ liệu cá nhân hay yêu cầu ngoài phạm vi.'}
    return {'output': json.dumps(result, ensure_ascii=False)}
