"""Jev supplies separate judgments; the caller decides acceptance."""
import logging
import os

from typesafe_sdk import Noul, TypeSafeClient, TypeSafeError

logger = logging.getLogger(__name__)


def judge_recommendation(client, evidence: dict, recommendation: dict) -> dict[str, float]:
    response = client.system_one(
        state={'evidence': evidence, 'recommendation': recommendation},
        questions={
            'grounded': Noul(instructions='Are the factual claims in `recommendation.content` supported by the numbers or source passages in `evidence`? A suggestion for an activity is not itself a factual claim.'),
            'relevant': Noul(instructions='Does the suggested activity in `recommendation.content` address the knowledge topic in `evidence.sources`?'),
        },
    )
    scores = {name: response.nouls[name].noul for name in ('grounded', 'relevant')}
    if any(type(score) not in (int, float) or not 0 <= score <= 1 for score in scores.values()):
        raise ValueError('Invalid JEV score')
    return scores


def score_demo_draft(evidence: dict, proposal: dict) -> dict[str, float] | None:
    key = os.getenv('TYPESAFE_API_KEY', '').strip()
    if not key:
        return None
    try:
        with TypeSafeClient(api_key=key, timeout=8) as client:
            return judge_recommendation(client, evidence, proposal)
    except (TypeSafeError, KeyError, TypeError, AttributeError, ValueError) as exc:
        logger.warning('Demo JEV unavailable (%s)', type(exc).__name__)
        return None
