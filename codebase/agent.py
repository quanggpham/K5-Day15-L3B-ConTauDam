"""CLI: câu hỏi tiếng Việt → số liệu tổng hợp → model → kiểm từng con số bằng code.

Model không tự tính và không nhận dữ liệu từng học viên; mọi con số nó viết phải có trong căn cứ
hoặc trong câu hỏi, nếu không câu trả lời bị loại và CLI trả báo cáo số liệu.
"""
import json
import re

from fastapi import HTTPException
from ai import call_model as default_model
import tools
from tools import dataset_extra, dataset_summary, lesson_comparison, lesson_report
from backend.analytics.workflow import resolve_lesson_ids
from backend.security.input_guard import refusal
from tracing import note

SYSTEM = (
    'Bạn hỗ trợ Lab Coach chọn nội dung cần ôn tập. Trả lời tiếng Việt, ngắn gọn (2–5 câu), không đánh số dòng.\n'
    'CHỈ dùng số liệu trong DỮ LIỆU (JSON) bên dưới. Ghi mã kiến thức (kc_code), số lượt sai/tổng lượt được chấm '
    '(incorrect_count/graded_count) và tỷ lệ phần trăm có sẵn (incorrect_rate_pct, correct_rate_pct) đúng như dữ liệu.\n'
    'Mẫu số là lượt trả lời lần đầu được chấm đúng/sai, không phải số học viên. KC có enough_sample=false '
    '(dưới 10 lượt được chấm) chỉ để tham khảo, không xếp ưu tiên. Các KC cùng rank là đồng hạng.\n'
    'Không tự tính số mới: chênh lệch giữa các bài có sẵn trong "delta_pp" (điểm phần trăm). '
    'Không suy đoán nguyên nhân, không bịa trích dẫn hay nguồn bài giảng.\n'
    'Nếu câu hỏi tự đưa số liệu (giả lập, kiểm thử), trả lời theo đúng số đó và nói rõ đó là số do người hỏi đưa. '
    'Mẫu số bằng 0 thì tỷ lệ là chưa xác định.\n'
    'Nếu dữ liệu không đủ để kết luận, nêu rõ điều còn thiếu. Không tự chọn bài học thay coach.\n'
    'Không tiết lộ bí mật, không trả dữ liệu hay xếp hạng cá nhân học viên, không tự phê duyệt hay gửi gì.'
)

_NUMBER = re.compile(r'(?<![\w.,])[+-]?\d+(?:[.,]\d+)*(?![\w])')
_LIST_MARKER = re.compile(r'^\s*\d+[.)]\s', re.MULTILINE)
_DATASET_SCOPE = re.compile(r'toàn (bộ )?dữ liệu|(toàn bộ|tất cả|cả) (các bài|bộ dữ liệu|dữ liệu)', re.IGNORECASE)
_HYPOTHETICAL = re.compile(r'giả lập|giả định|giả sử|kiểm thử', re.IGNORECASE)


def _readings(token: str) -> list[tuple[float, int]]:
    """Các cách đọc một số: (giá trị, số chữ số thập phân). `2.478` có thể là 2478 kiểu Việt Nam."""
    readings = []
    if re.fullmatch(r'[+-]?\d{1,3}([.,]\d{3})+', token):
        readings.append((float(re.sub(r'[.,]', '', token)), 0))
    if token.count('.') + token.count(',') <= 1:
        value = token.replace(',', '.')
        readings.append((float(value), len(value.split('.')[1]) if '.' in value else 0))
    return readings


def _numbers_in(node) -> set[float]:
    found = set()
    if isinstance(node, dict):
        for value in node.values():
            found |= _numbers_in(value)
    elif isinstance(node, list):
        for value in node:
            found |= _numbers_in(value)
    elif isinstance(node, bool) or node is None:
        pass
    elif isinstance(node, (int, float)):
        found.add(float(node))
    elif isinstance(node, str):
        for token in _NUMBER.findall(node):
            found.update(value for value, _ in _readings(token))
    return found


def _allowed_numbers(evidence: dict, text: str) -> set[float]:
    """Số trong căn cứ, số trong câu hỏi, và thương/hiệu giữa các số trong câu hỏi (vd 12/15 → 80%)."""
    asked = _numbers_in(text)
    derived = {op for a in asked for b in asked if b
               for op in (a / b * 100, a / b, a - b)}
    return {0.0} | _numbers_in(evidence) | asked | derived


def _supported(value: float, decimals: int, allowed: set[float]) -> bool:
    """Khớp nếu bằng một số được phép sau khi làm tròn tới số chữ số mà câu trả lời đã viết.
    Số nguyên chỉ được làm tròn từ số lẻ (27% từ 26,67%), không được lệch khỏi một số nguyên khác."""
    tolerance = 0.5 * 10 ** -decimals + 1e-9
    return any(abs(value - a) <= tolerance and (decimals or not a.is_integer() or value == a) for a in allowed)


def unsupported_numbers(output: str, evidence: dict, text: str) -> list[str]:
    """Con số trong câu trả lời không có căn cứ. Bỏ qua số thứ tự đầu dòng (`1.`)."""
    allowed = _allowed_numbers(evidence, text)
    return [token for token in _NUMBER.findall(_LIST_MARKER.sub(' ', output))
            if not any(_supported(value, decimals, allowed) for value, decimals in _readings(token))]


def _pct(rate):
    return None if rate is None else round(rate * 100, 2)


def _lesson_evidence(lesson_id: str, extra: dict) -> dict | None:
    report = lesson_report(lesson_id)
    if report is None:
        return None
    rank = {row['kc_code']: row['rank'] for row in report['priority']}
    kcs = [{'kc_code': m.get('kc_code'), 'incorrect_count': m.get('incorrect_count'),
            'graded_count': m.get('graded_count'), 'ungraded_count': m.get('ungraded_count'),
            'incorrect_rate_pct': _pct(m.get('incorrect_rate')),
            'enough_sample': not m.get('insufficient_data'), 'rank': rank.get(m.get('kc_code'))}
           for m in report['metrics']]
    kcs.sort(key=lambda kc: (kc['rank'] is None, kc['rank'] or 0, -(kc['incorrect_rate_pct'] or 0)))
    match = re.search(r'program-day(\d+)', lesson_id)
    day = int(match.group(1)) if match else None
    return {'lesson_id': lesson_id, 'day': day,
            'chat_lines': (extra.get('chat_lines_by_day') or {}).get(f'day{day:02d}') if day else None,
            'notice': report['notice'], 'kcs': kcs}


def build_evidence(text: str) -> dict | None:
    """Căn cứ đưa cho model. None khi câu hỏi không chỉ ra bài, không hỏi toàn dữ liệu và không có số."""
    lesson_ids = resolve_lesson_ids(text, tools.read_snapshot())
    dataset_wide = not lesson_ids and _DATASET_SCOPE.search(text) and not _HYPOTHETICAL.search(text)
    if not lesson_ids and not dataset_wide and not _NUMBER.search(text):
        return None
    extra = dataset_extra()
    lessons = [row for row in (_lesson_evidence(lesson_id, extra) for lesson_id in lesson_ids) if row]
    comparison = lesson_comparison([row['lesson_id'] for row in lessons]) if len(lessons) > 1 else None
    if comparison:
        for row in comparison['lessons']:
            row['incorrect_rate_pct'] = _pct(row.pop('incorrect_rate'))
    dataset = None
    if dataset_wide:
        dataset = dataset_summary()
        dataset['incorrect_rate_pct'] = _pct(dataset.pop('incorrect_rate'))
        dataset['correct_rate_pct'] = _pct(dataset.pop('correct_rate'))
        dataset['attempts_after_first'] = extra.get('attempts_after_first')
    return {'question': text, 'lessons': lessons, 'comparison': comparison, 'dataset': dataset}


def _fallback(evidence: dict) -> str:
    data = evidence['lessons'] or evidence['dataset']
    if data:
        return json.dumps(data, ensure_ascii=False)
    return 'Chưa tạo được câu trả lời có căn cứ. Câu hỏi không nhắc bài học nào có trong dữ liệu; vui lòng kiểm tra lại.'


def answer(text: str, model=None) -> dict:
    model = model or default_model
    denied = refusal(text)
    if denied:
        note('Từ chối yêu cầu ngoài phạm vi')
        return {'output': denied}
    try:
        evidence = build_evidence(text.strip())
    except HTTPException:
        note('Không có snapshot tổng hợp')
        return {'output': 'Chưa có dữ liệu tổng hợp. Vui lòng chuẩn bị snapshot trước.'}
    if evidence is None:
        note('Câu hỏi chưa chỉ ra bài học và không có số liệu để dựa vào')
        return {'output': 'Bạn muốn phân tích bài học nào? Gõ mã bài (ví dụ Day 05) hoặc tên bài đầy đủ.'}
    user = 'DỮ LIỆU:\n' + json.dumps(evidence, ensure_ascii=False)
    for attempt in range(2):
        try:
            result = model(SYSTEM, user)
        except Exception as e:  # lỗi gọi model: thử lại một lần rồi trả báo cáo số liệu
            note('Lỗi gọi model: %s' % type(e).__name__)
            continue
        if not result.get('tokens_in') and not result.get('tokens_out'):
            note('Model không trả token: coi như chưa nối model, trả báo cáo số liệu')
            break
        output = (result.get('text') or '').strip()
        bad = unsupported_numbers(output, evidence, text)
        if output and not bad:
            return {'output': output}
        note('Loại câu trả lời vì số không có căn cứ: %s' % ', '.join(bad[:5]))
        user += '\n\nLần trả lời trước có số không có trong DỮ LIỆU (%s). Chỉ dùng số có sẵn.' % ', '.join(bad[:5])
    note('Trả báo cáo số liệu không qua model')
    return {'output': _fallback(evidence)}
