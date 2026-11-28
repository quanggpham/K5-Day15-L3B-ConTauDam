import importlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'codebase'))

SNAPSHOT = {
    'program-day05:a': [{'kc_code': 'KC1', 'graded_count': 15, 'incorrect_count': 12, 'ungraded_count': 0,
                         'incorrect_rate': 0.8}],
    'program-day07:b': [{'kc_code': 'KC2', 'graded_count': 10, 'incorrect_count': 6, 'ungraded_count': 0,
                         'incorrect_rate': 0.6}],
}


@pytest.fixture
def agent(monkeypatch):
    agent = importlib.import_module('agent')
    tools = importlib.import_module('tools')
    monkeypatch.setattr(tools, 'read_snapshot', lambda: SNAPSHOT)
    monkeypatch.setattr(agent, 'dataset_extra', lambda: {'chat_lines_by_day': {'day05': 102}, 'attempts_after_first': 18})
    state = {'reply': '', 'error': None, 'calls': []}

    def model(system, user):
        state['calls'].append((system, user))
        if state['error']:
            raise state['error']
        return {'text': state['reply'], 'model': 'fake-test', 'tokens_in': 10, 'tokens_out': 5}

    monkeypatch.setattr(agent, 'default_model', model)
    agent.state = state
    return agent


def test_question_in_words_gets_lesson_data_and_model_answer(agent):
    agent.state['reply'] = 'Nên ưu tiên KC1: 12/15 lượt sai (80%).'
    out = agent.answer('Lab Coach chuẩn bị ôn Day 05, nên ưu tiên kiến thức nào?')['output']
    assert out == 'Nên ưu tiên KC1: 12/15 lượt sai (80%).'
    assert len(agent.state['calls']) == 1
    evidence = agent.state['calls'][0][1]
    assert 'KC1' in evidence and '12' in evidence
    assert 'hv' not in evidence


def test_lesson_evidence_carries_chat_line_count(agent):
    evidence = agent.build_evidence('Trong Day 05 có bao nhiêu dòng chat?')
    assert evidence['lessons'][0]['chat_lines'] == 102


def test_model_may_only_use_numbers_from_data_or_question(agent):
    agent.state['reply'] = 'KC X sai 12/15 lượt lần đầu, tức 80%; chưa có tài liệu bài giảng.'
    out = agent.answer('KC X sai 12/15 lượt lần đầu, chưa có tài liệu. Hãy đề xuất cách ôn.')['output']
    assert '80%' in out and len(agent.state['calls']) == 1


def test_hypothetical_numbers_do_not_pull_in_dataset_totals(agent):
    evidence = agent.build_evidence('Dữ liệu giả lập: KC A sai 3/10 lượt. Có nên ưu tiên không?')
    assert evidence['lessons'] == [] and evidence['dataset'] is None


def test_dataset_wide_question_without_digits_gets_dataset_totals(agent):
    agent.state['reply'] = 'Toàn bộ dữ liệu có 18/25 lượt sai, tức 72%; loại 18 lượt lần hai.'
    out = agent.answer('Tỷ lệ sai lần đầu trên toàn bộ dữ liệu là bao nhiêu?')['output']
    assert out.startswith('Toàn bộ dữ liệu')
    evidence = json.loads(agent.state['calls'][0][1].removeprefix('DỮ LIỆU:\n'))
    assert evidence['dataset']['graded_count'] == 25 and evidence['dataset']['attempts_after_first'] == 18


def test_rounded_and_vietnamese_formatted_numbers_are_accepted(agent):
    evidence = {'lessons': [{'graded_count': 2478, 'incorrect_rate_pct': 26.6667}]}
    assert agent.unsupported_numbers('1. Có 2.478 lượt, khoảng 27% hay 26,67% sai.', evidence, '') == []
    assert agent.unsupported_numbers('Có 2479 lượt.', evidence, '') == ['2479']


def test_invented_number_is_retried_once_then_falls_back_to_report(agent):
    agent.state['reply'] = 'KC1 sai 99% lượt.'
    out = agent.answer('Trong Day 05, KC nào sai nhiều nhất?')['output']
    assert len(agent.state['calls']) == 2
    assert '99' not in agent.state['calls'][1][1]
    assert '"kc_code": "KC1"' in out and '99' not in out


def test_comparison_numbers_come_from_tool_not_from_model(agent):
    agent.state['reply'] = 'Day05 có tỷ lệ sai cao hơn Day07 20 điểm phần trăm.'
    out = agent.answer('Day 05 và Day 07, bài nào sai nhiều hơn?')['output']
    evidence = agent.state['calls'][0][1]
    assert 'delta_pp' in evidence and '20.0' in evidence
    assert 'Day07' in out


def test_no_lesson_and_no_numbers_asks_instead_of_guessing(agent):
    out = agent.answer('Hãy phân tích bài học cần ôn hôm nay. Tôi chưa chọn bài học.')['output']
    assert 'bài học' in out and agent.state['calls'] == []


def test_model_error_keeps_metrics_report(agent):
    agent.state['error'] = RuntimeError('hết lượt')
    out = agent.answer('Day 05 nên ôn gì?')['output']
    assert '"kc_code": "KC1"' in out
    assert len(agent.state['calls']) == 2


def test_model_without_tokens_is_treated_as_not_connected(agent, monkeypatch):
    monkeypatch.setattr(agent, 'default_model',
                        lambda s, u: {'text': '[giả] 12', 'model': 'fake', 'tokens_in': 0, 'tokens_out': 0})
    out = agent.answer('Day 05 nên ôn gì?')['output']
    assert '"kc_code": "KC1"' in out and '[giả]' not in out
def test_sensitive_cli_data_stays_out_of_model_input_and_response(agent):
    for marker in ('coach@example.invalid', 'L123456', '2A202603952', 'sk-syntheticfixture000000000000'):
        assert 'định danh' in agent.answer(f'Ôn Day 05, tham chiếu {marker}')['output']
    assert agent.state['calls'] == []
    agent.state['reply'] = 'Liên hệ coach@example.invalid.'
    assert 'coach@example.invalid' not in agent.answer('Ôn Day 05')['output']
    assert all('coach@example.invalid' not in prompt for _, prompt in agent.state['calls'])


def test_cli_excludes_small_group_metrics(agent, monkeypatch):
    report = {'priority': [], 'notice': '', 'metrics': [
        {'kc_code': 'private_group', 'status': 'small_group', 'graded_count': 73},
        {'kc_code': 'KC1', 'status': 'ok', 'graded_count': 15, 'incorrect_rate': 0.8},
    ]}
    monkeypatch.setattr(agent, 'lesson_report', lambda lesson_id: report)
    agent.state['reply'] = 'KC1: 80% sai.'
    assert agent.answer('Xem Day 05')['output'] == 'KC1: 80% sai.'
    payload = agent.state['calls'][0][1]
    assert 'private_group' not in payload and '73' not in payload
