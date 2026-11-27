from codebase.backend.rag.retrieval import retrieve


def test_retrieval_filters_lesson_and_kc_and_respects_approval():
    docs = [
        {'id':'a','lesson_id':'L1','kc_code':'K1','text':'Mô hình phân loại lỗi trong ví dụ','approved':True},
        {'id':'b','lesson_id':'L2','kc_code':'K1','text':'lỗi lỗi lỗi','approved':True},
        {'id':'c','lesson_id':'L1','kc_code':'K1','text':'lỗi bí mật','approved':False},
        {'id':'d','lesson_id':'L1','kc_code':'K2','text':'lỗi lỗi','approved':True},
    ]
    result = retrieve(docs, 'L1','K1','phân loại lỗi')
    assert [doc['id'] for doc in result] == ['a']
    assert retrieve(docs,'L9','K1','lỗi') == []
