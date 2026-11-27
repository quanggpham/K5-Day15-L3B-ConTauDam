"""Reject clearly disallowed requests before looking up data or calling models."""
import re


def refusal(text: str) -> str | None:
    value = ' '.join(text.casefold().split())
    if re.search(r'api[\s_-]*key|secret|mật khẩu|bí mật|bỏ qua.{0,30}(quy tắc|hướng dẫn)|ignore.{0,30}(instructions|rules)', value):
        return 'Không thực hiện chỉ dẫn vượt quy tắc hoặc tiết lộ bí mật.'
    if re.search(r'(học viên|người học|student)', value) and re.search(r'(cá nhân|xếp hạng|yếu nhất|danh sách|tên|email|mã|rank|identity)', value):
        return 'Không cung cấp danh tính hay xếp hạng cá nhân; có thể xem số liệu tổng hợp theo KC.'
    if re.search(r'phê duyệt|gửi lịch|gửi tin|approve|send (?:a |the )?(?:message|schedule)', value):
        return 'Không tự phê duyệt hay gửi; coach cần xem xét và xác nhận bản nháp.'
    return None
