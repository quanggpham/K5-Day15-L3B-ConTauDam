"""Jev supplies separate judgments; the caller decides acceptance."""
from typesafe_sdk import Noul


def judge_recommendation(client, evidence: dict, recommendation: dict) -> dict[str, float]:
    response = client.system_one(
        state={'evidence': evidence, 'recommendation': recommendation},
        questions={
            'grounded': Noul(instructions='Are the factual claims in `recommendation.content` supported by the numbers or source passages in `evidence`? A suggestion for an activity is not itself a factual claim.'),
            'relevant': Noul(instructions='Does the suggested activity in `recommendation.content` address the knowledge topic in `evidence.sources`?'),
        },
    )
    return {name: response.nouls[name].noul for name in ('grounded', 'relevant')}
