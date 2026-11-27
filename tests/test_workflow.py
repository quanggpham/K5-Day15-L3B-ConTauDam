from codebase.backend.analytics.workflow import create_report


def test_report_ranks_only_sufficient_graded_groups():
    snapshot = {'L1': [
        {'kc_code':'K1','graded_count':10,'incorrect_count':4,'ungraded_count':1,'incorrect_rate':0.4},
        {'kc_code':'K2','insufficient_data':True},
        {'kc_code':'K3','graded_count':0,'incorrect_count':0,'ungraded_count':6,'incorrect_rate':None},
        {'kc_code':'K4','graded_count':5,'incorrect_count':4,'ungraded_count':0,'incorrect_rate':0.8},
    ]}
    result = create_report('L1', snapshot)
    assert [row['kc_code'] for row in result['priority']] == ['K4', 'K1']
    assert result['metrics'][1]['insufficient_data'] is True
    assert 'Chưa có căn cứ' in result['notice']
    assert create_report('no', snapshot) is None
