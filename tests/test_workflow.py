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


def test_equal_rates_share_rank():
    snapshot = {'L1': [
        {'kc_code':'B','graded_count':20,'incorrect_count':8,'ungraded_count':0,'incorrect_rate':0.4},
        {'kc_code':'A','graded_count':10,'incorrect_count':4,'ungraded_count':0,'incorrect_rate':0.4},
        {'kc_code':'C','graded_count':10,'incorrect_count':1,'ungraded_count':0,'incorrect_rate':0.1},
    ]}
    result = create_report('L1', snapshot)
    assert [(item['kc_code'],item['rank']) for item in result['priority']] == [('A',1),('B',1),('C',3)]


from codebase.backend.analytics.workflow import resolve_lesson_id, resolve_lesson_ids

SNAP = {'program-day05:a-b': [], 'program-day07:c-d': [], 'program-day12:e-f': []}


def test_resolve_finds_every_lesson_mentioned_in_a_sentence():
    text = 'So sánh tỷ lệ sai lần đầu của Day05 và Day 07 cho Lab Coach'
    assert resolve_lesson_ids(text, SNAP) == ['program-day05:a-b', 'program-day07:c-d']


def test_resolve_reports_dataset_wide_or_unspecified_question_as_empty():
    assert resolve_lesson_ids('Tỷ lệ sai lần đầu toàn bộ dữ liệu là bao nhiêu?', SNAP) == []
    assert resolve_lesson_ids('Tôi chưa chọn ngày hoặc bài học.', SNAP) == []


def test_resolve_keeps_first_match_and_rejects_ambiguous_day():
    assert resolve_lesson_id('Trong Day 07 nên ôn KC nào?', SNAP) == 'program-day07:c-d'
    assert resolve_lesson_id('Day 99', SNAP) is None
