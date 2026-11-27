import duckdb
from codebase.backend.analytics.metrics import lesson_metrics


def test_metrics_exclude_ungraded_and_retries():
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', [('L1','K1',1,False,'a'),('L1','K1',1,True,'b'),('L1','K1',1,None,'c'),('L1','K1',2,True,'a'),('L2','K1',1,False,'d')])
    assert lesson_metrics(db, 'L1') == [{'kc_code':'K1','graded_count':2,'incorrect_count':1,'ungraded_count':1,'incorrect_rate':0.5}]
    assert lesson_metrics(db, 'unknown') == []


def test_ungraded_and_parameterized_lesson():
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.execute("insert into answers values ('L1', 'K1', 1, null, 'person')")
    result = lesson_metrics(db, 'L1')
    assert result[0]['incorrect_rate'] is None
    assert result[0]['ungraded_count'] == 1
    assert 'hv' not in result[0]
    assert lesson_metrics(db, "L1' OR true --") == []


def test_snapshot_marks_small_groups():
    from codebase.backend.analytics.metrics import export_snapshot
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', [('L','small',1,False,'a')] + [('L','enough',1,False,str(i)) for i in range(10)])
    result = export_snapshot(db)
    assert result == {'L': [{'kc_code':'enough','graded_count':10,'incorrect_count':10,'ungraded_count':0,'incorrect_rate':1.0},{'kc_code':'small','graded_count':1,'incorrect_count':1,'ungraded_count':0,'incorrect_rate':1.0,'insufficient_data':True}]}
    assert 'hv' not in str(result)


def test_snapshot_marks_when_only_one_learner_graded():
    from codebase.backend.analytics.metrics import export_snapshot
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', [('L','K',1,False,'a')] + [('L','K',1,None,str(i)) for i in range(4)])
    assert export_snapshot(db)['L'] == [{'kc_code':'K','graded_count':1,'incorrect_count':1,'ungraded_count':4,'incorrect_rate':1.0,'insufficient_data':True}]


def test_priority_requires_ten_graded_responses():
    from codebase.backend.analytics.metrics import export_snapshot
    from codebase.backend.analytics.workflow import create_report
    db = duckdb.connect(':memory:')
    db.execute('create table answers (lesson_id varchar, kc_code varchar, lan_thu int, was_correct boolean, hv varchar)')
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', [('L','K',1,False,str(i)) for i in range(5)])
    report = create_report('L', export_snapshot(db))
    assert report['priority'] == []
    assert report['metrics'][0]['insufficient_data'] is True
    db.executemany('insert into answers values (?, ?, ?, ?, ?)', [('L','K',1,True,str(i)) for i in range(5)])
    report = create_report('L', export_snapshot(db))
    assert report['priority'][0]['kc_code'] == 'K'
    assert report['priority'][0]['graded_count'] == 10
