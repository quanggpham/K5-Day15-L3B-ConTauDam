"""Reject clearly disallowed requests before looking up data or calling models."""
import re


_SENSITIVE = re.compile(
    r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\bL\d{4,}\b|\b2A\d{7,}\b|'
    r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    re.IGNORECASE,
)


def contains_sensitive(text: str) -> bool:
    return bool(_SENSITIVE.search(text))


def refusal(text: str) -> str | None:
    if contains_sensitive(text):
        return 'Vui lòng bỏ thông tin định danh hoặc khóa khỏi câu hỏi.'
    value = ' '.join(text.casefold().split())
    if re.search(r'api[\s_-]*key|secret|mật khẩu|bí mật|bỏ qua.{0,30}(quy tắc|hướng dẫn)|ignore.{0,30}(instructions|rules)', value):
        return 'Không thực hiện chỉ dẫn vượt quy tắc hoặc tiết lộ bí mật.'
    if re.search(r'(học viên|người học|student)', value) and re.search(r'(cá nhân|xếp hạng|yếu nhất|danh sách|tên|email|mã|rank|identity)', value):
        return 'Không cung cấp danh tính hay xếp hạng cá nhân; có thể xem số liệu tổng hợp theo KC.'
    if re.search(r'phê duyệt|gửi lịch|gửi tin|approve|send (?:a |the )?(?:message|schedule)', value):
        return 'Không tự phê duyệt hay gửi; coach cần xem xét và xác nhận bản nháp.'
    return None
