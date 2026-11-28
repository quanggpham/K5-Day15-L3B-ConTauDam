import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'codebase'))


@pytest.fixture
def tools(monkeypatch):
    tools = importlib.import_module('tools')
    snapshot = {
        'program-day05:a': [
            {'kc_code': 'KC1', 'graded_count': 10, 'incorrect_count': 4, 'ungraded_count': 0, 'incorrect_rate': 0.4},
            {'kc_code': 'KC2', 'graded_count': 5, 'incorrect_count': 0, 'ungraded_count': 0, 'incorrect_rate': 0.0},
        ],
        'program-day07:b': [
            {'kc_code': 'KC1', 'graded_count': 10, 'incorrect_count': 1, 'ungraded_count': 2, 'incorrect_rate': 0.1},
        ],
    }
    monkeypatch.setattr(tools, 'read_snapshot', lambda: snapshot)
    return tools


def test_comparison_has_rates_and_delta_in_percentage_points(tools):
    result = tools.lesson_comparison(['program-day05:a', 'program-day07:b'])
    assert [row['lesson_id'] for row in result['lessons']] == ['program-day05:a', 'program-day07:b']
    assert result['lessons'][0] == {'lesson_id': 'program-day05:a', 'graded_count': 15, 'incorrect_count': 4,
                                    'ungraded_count': 0, 'incorrect_rate': pytest.approx(4 / 15)}
    assert result['lessons'][1]['ungraded_count'] == 2
    assert result['delta_pp']['program-day05:a']['program-day07:b'] == pytest.approx(16.67)


def test_comparison_is_none_for_unknown_lesson(tools):
    assert tools.lesson_comparison(['program-day05:a', 'nope']) is None


def test_dataset_summary_counts_attempts_not_learners(tools):
    summary = tools.dataset_summary()
    assert (summary['graded_count'], summary['incorrect_count'], summary['ungraded_count']) == (25, 5, 2)
    assert summary['correct_count'] == 20
    assert summary['correct_rate'] == pytest.approx(0.8)
    assert summary['lessons'] == ['program-day05:a', 'program-day07:b']
    assert 'hv' not in str(summary)


def test_dataset_extra_is_empty_when_file_missing(tools, monkeypatch, tmp_path):
    monkeypatch.setattr(tools, 'EXTRA_COUNTS_PATH', str(tmp_path / 'missing.json'))
    assert tools.dataset_extra() == {}


def test_example_tool_is_gone(tools):
    assert 'search_example' not in importlib.import_module('tracing').TOOLS
