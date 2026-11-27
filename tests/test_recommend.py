import json
from codebase.backend.agents.recommend import generate_recommendations


def inputs():
    report = {'lesson_id':'L1','priority':[{'kc_code':'K1','graded_count':10,'incorrect_count':4,'ungraded_count':0,'incorrect_rate':0.4}]}
    docs = [{'id':'D1','lesson_id':'L1','kc_code':'K1','approved':True,'text':'Giải thích khái niệm K1 bằng ví dụ.'}]
    return report, docs


def test_missing_knowledge_does_not_call_model():
    report, _ = inputs()
    def unexpected(*args): raise AssertionError('must not call')
    result = generate_recommendations(report, [], unexpected, unexpected)
    assert result['status'] == 'missing_knowledge'
    assert result['recommendations'] == []


def test_valid_recommendation_requires_judge_and_citation():
    report, docs = inputs()
    proposal = {'kc_code':'K1','content':'Có 4 lượt sai trên 10 lượt.','citations':['D1']}
    calls = []
    def model(system, user):
        calls.append(user)
        return {'text':json.dumps([proposal])}
    def judge(evidence, recommendation):
        assert evidence['lesson_id'] == 'L1'
        return {'grounded':0.95,'relevant':0.94}
    result = generate_recommendations(report, docs, model, judge)
    assert result['status'] == 'ok' and result['recommendations'] == [proposal]
    assert len(calls) == 1


def test_invalid_output_fails_closed_after_one_retry():
    report, docs = inputs()
    calls = []
    def model(system, user):
        calls.append(1)
        return {'text':json.dumps([{'kc_code':'K1','content':'Có 99 lượt sai.','citations':['D1']}])}
    def judge(*args): raise AssertionError('invalid output must not be judged')
    result = generate_recommendations(report, docs, model, judge)
    assert result['status'] == 'validation_failed' and result['recommendations'] == []
    assert len(calls) == 2


def test_knowledge_excludes_extra_fields_and_blocks_obvious_personal_data():
    report, docs = inputs()
    docs[0]['hv'] = 'L1234'
    proposal = {'kc_code':'K1','content':'Có 4 lượt sai trên 10 lượt.','citations':['D1']}
    def model(system, user):
        assert 'L1234' not in user and '"hv"' not in user
        return {'text':json.dumps([proposal])}
    def judge(*args): return {'grounded':0.99,'relevant':0.99}
    assert generate_recommendations(report, docs, model, judge)['status'] == 'ok'
    docs[0]['text'] = 'Thông tin liên hệ test@example.org'
    assert generate_recommendations(report, docs, model, judge)['status'] == 'unsafe_knowledge'


def test_low_judge_score_and_model_failure_return_no_recommendations():
    report, docs = inputs()
    proposal = {'kc_code':'K1','content':'Có 4 lượt sai trên 10 lượt.','citations':['D1']}
    calls = []
    def model(system, user):
        calls.append(1)
        return {'text':json.dumps([proposal])}
    result = generate_recommendations(report, docs, model, lambda *args: {'grounded':0.89,'relevant':0.99})
    assert result['status'] == 'validation_failed' and result['recommendations'] == []
    assert len(calls) == 2
    def offline(*args): raise RuntimeError('provider down')
    assert generate_recommendations(report, docs, offline, lambda *args: {})['status'] == 'model_error'


def test_tie_at_selection_boundary_requires_review():
    report, docs = inputs()
    report['priority'] = [dict(report['priority'][0], kc_code=f'K{i}', incorrect_rate=0.4) for i in range(4)]
    def unexpected(*args): raise AssertionError('must not arbitrarily split a tie')
    result = generate_recommendations(report, docs, unexpected, unexpected)
    assert result['status'] == 'tie_needs_review'
    assert result['recommendations'] == []
