"""Deterministic checks are a first gate, not a substitute for human or JEV review."""
import math
import re


def validate_recommendation(recommendation: dict, evidence: dict, sources: list[dict]) -> dict:
    if not isinstance(recommendation, dict) or set(recommendation) != {'kc_code', 'content', 'citations'}:
        raise ValueError('Định dạng đề xuất không hợp lệ')
    content, citations = recommendation['content'], recommendation['citations']
    if (not isinstance(evidence.get('lesson_id'), str) or not evidence['lesson_id']
            or not isinstance(evidence.get('kc_code'), str) or not evidence['kc_code']
            or recommendation['kc_code'] != evidence.get('kc_code') or evidence.get('insufficient_data')
            or not isinstance(content, str) or not content.strip()
            or not isinstance(citations, list) or not citations or not all(isinstance(c, str) for c in citations)):
        raise ValueError('Đề xuất không khớp số liệu')
    permitted = {s['id'] for s in sources if s.get('approved') is True and s.get('lesson_id') == evidence.get('lesson_id')
                 and s.get('kc_code') == evidence.get('kc_code') and isinstance(s.get('id'), str)}
    if not set(citations) <= permitted:
        raise ValueError('Trích dẫn không hợp lệ')
    if re.search(r'\bL\d{4,}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', content, re.IGNORECASE):
        raise ValueError('Có khả năng chứa thông tin cá nhân')
    allowed = set()
    for key in ('graded_count', 'incorrect_count', 'ungraded_count', 'incorrect_rate'):
        value = evidence.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            allowed.add(float(value))
            if key == 'incorrect_rate':
                allowed.add(round(float(value) * 100, 2))
    for token in re.findall(r'(?<![\w])[+-]?\d+(?:[.,]\d+)?(?:[eE][+-]?\d+)?(?![\w])', content):
        if float(token.replace(',', '.')) not in allowed:
            raise ValueError('Số liệu không có trong căn cứ')
    return recommendation
