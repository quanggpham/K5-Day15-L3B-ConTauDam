"""Promptfoo adapter. Uses only the synthetic snapshot below."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'codebase'))
import agent
import tools
from ai import MODEL_PROVIDER, call_model


def call_api(prompt, options, context):
    tools.read_snapshot = lambda: {'program-day05:synthetic': [
        {'kc_code': 'practice', 'incorrect_count': 12, 'graded_count': 15,
         'ungraded_count': 0, 'incorrect_rate': 0.8},
    ]}
    agent.dataset_extra = lambda: {}
    if MODEL_PROVIDER != 'liquid':
        return {'error': 'Configure MODEL_PROVIDER=liquid, MODEL_NAME and LIQUID_API_KEY.'}
    calls = 0
    live_results = 0

    def model(system, user):
        nonlocal calls, live_results
        calls += 1
        result = call_model(system, user)
        live_results += bool(result['tokens_in'] and result['tokens_out'])
        return result

    return {'output': dict(agent.answer(prompt, model=model), calls=calls, live_results=live_results)}
