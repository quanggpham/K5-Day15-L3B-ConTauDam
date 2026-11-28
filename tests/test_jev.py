from types import SimpleNamespace
from codebase.backend.evaluation.jev import judge_recommendation


def test_judge_sends_separate_questions_and_returns_scores():
    class FakeClient:
        def system_one(self, *, state, questions):
            assert state['evidence']['kc_code'] == 'KC1'
            assert set(questions) == {'grounded', 'relevant'}
            return SimpleNamespace(nouls={'grounded': SimpleNamespace(noul=0.9), 'relevant': SimpleNamespace(noul=0.8)})
    assert judge_recommendation(FakeClient(), {'kc_code':'KC1'}, {'content':'Ôn lại ví dụ'}) == {'grounded':0.9,'relevant':0.8}



def test_demo_jev_unavailable_keeps_preview_unscored(monkeypatch):
    from codebase.backend.evaluation import jev
    from typesafe_sdk import TypeSafeAPIConnectionError

    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    assert jev.score_demo_draft({}, {}) is None
    monkeypatch.setenv('TYPESAFE_API_KEY', 'synthetic')
    def offline(**kwargs):
        raise TypeSafeAPIConnectionError(message='provider unavailable')
    monkeypatch.setattr(jev, 'TypeSafeClient', offline)
    assert jev.score_demo_draft({}, {}) is None
