"""Jev supplies separate judgments; the caller decides acceptance."""
from typesafe_sdk import Noul


def judge_recommendation(client, evidence: dict, recommendation: dict) -> dict[str, float]:
    response = client.system_one(
        state={'evidence': evidence, 'recommendation': recommendation},
        questions={
            'grounded': Noul(instructions='Are all factual claims in `recommendation` supported by `evidence`?'),
            'relevant': Noul(instructions='Does `recommendation` address the knowledge gap identified in `evidence`?'),
        },
    )
    return {name: response.nouls[name].noul for name in ('grounded', 'relevant')}
