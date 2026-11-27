import pytest
from codebase.backend.security.output_guard import validate_recommendation


def test_output_requires_valid_evidence_and_citations():
    evidence = {'lesson_id':'L1', 'kc_code':'KC1', 'graded_count':10, 'incorrect_count':4, 'incorrect_rate':0.4}
    sources = [{'id':'S1','lesson_id':'L1','kc_code':'KC1','approved':True,'text':'Nội dung được phép'}]
    good = {'kc_code':'KC1','content':'Có 4 lượt sai trên 10 lượt.','citations':['S1']}
    assert validate_recommendation(good, evidence, sources) == good
    for bad in [
        {**good, 'citations':['unknown']},
        {**good, 'kc_code':'KC2'},
        {**good, 'content':'Có 99 lượt sai.'},
        {**good, 'content':'Có -4 lượt sai.'},
        {**good, 'content':'Có 4e2 lượt sai.'},
        {**good, 'content':'Mã học viên L0001'},
        {**good, 'content':'Liên hệ test@example.org'},
    ]:
        with pytest.raises(ValueError):
            validate_recommendation(bad, evidence, sources)
