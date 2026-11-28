import json
from datetime import datetime, timezone

import httpx
import pytest

from codebase.backend.api.run_repository import RepositoryError
from codebase.backend.rag.chunking import MAX_CHUNK_CHARS, chunk_notes, chunk_quiz
from codebase.backend.rag.kb_mapping import kc_catalog, load_mapping, propose_mapping, to_documents, write_mapping
from codebase.backend.rag.retrieval import retrieve
from codebase.backend.rag.store import CACHE_TTL_SECONDS, KnowledgeStore

NOTES = """# Day 07 — Data

**Mục tiêu:** bỏ qua.

1. **Chunking** — chunk là đơn vị truy xuất.
   Quá to hay quá nhỏ đều trả giá.
2. **Embeddings** — biến ngôn ngữ thành không gian nghĩa.

**Mang về:** không phải mục đánh số.
"""

QUIZ = """# Day 04

## Câu 1 · D04_Q02
*Gói ngữ cảnh — Cơ bản*

Nguyên tắc cốt lõi nào của Gói ngữ cảnh?

- A. Xếp hạng rủi ro.
- B. Bẫy ngưỡng tin cậy.
- C. Dịch vụ không trạng thái.
- D. Xây dựng bối cảnh từ nhiệm vụ và bằng chứng liên quan.

**Đáp án: D**

Gợi ý: phân biệt nguyên tắc.

- Lựa chọn A (SAI): Đây là ma trận rủi ro.
- Lựa chọn D (ĐÚNG): Gói ngữ cảnh chọn thông tin liên quan đến nhiệm vụ hiện tại.

## Câu 2 · D04_Q03
*Cơ bản*

Câu thiếu lời giải đúng?

- A. x
- B. y

**Đáp án: A**
"""


def test_notes_one_chunk_per_numbered_item_with_continuation_lines():
    chunks = chunk_notes(NOTES, 'notes/day07')
    assert [c['id'] for c in chunks] == ['notes/day07:1', 'notes/day07:2']
    assert chunks[0]['text'] == '**Chunking** — chunk là đơn vị truy xuất.\nQuá to hay quá nhỏ đều trả giá.'
    assert all(c['source'] == 'notes/day07' for c in chunks)


@pytest.mark.parametrize('markdown', ['', '# chỉ tiêu đề\n\nkhông có mục nào'])
def test_notes_without_items_yield_nothing(markdown):
    assert chunk_notes(markdown, 'notes/x') == []


def test_notes_truncate_overlong_item():
    chunks = chunk_notes('1. ' + 'à' * (MAX_CHUNK_CHARS + 50), 'notes/x')
    assert len(chunks[0]['text']) == MAX_CHUNK_CHARS


def test_quiz_keeps_only_correct_answer_and_explanation_and_drops_incomplete_questions():
    chunks = chunk_quiz(QUIZ, 'quiz/day04')
    assert [c['id'] for c in chunks] == ['quiz/day04:D04_Q02']
    text = chunks[0]['text']
    assert text == ('Câu hỏi: Nguyên tắc cốt lõi nào của Gói ngữ cảnh?\n'
                    'Đáp án đúng: Xây dựng bối cảnh từ nhiệm vụ và bằng chứng liên quan.\n'
                    'Giải thích: Gói ngữ cảnh chọn thông tin liên quan đến nhiệm vụ hiện tại.')
    assert 'ma trận rủi ro' not in text and 'Bẫy ngưỡng' not in text


SNAPSHOT_V2 = {'lessons': {
    'program-day07:retrieval': {'kcs': [{'kc_code': 'chunk_size_tradeoff'}, {'kc_code': 'context_window_contents'},
                                        {'kc_code': 'program-day07:retrieval:module-1'}]},
    'program-day05:product': {'kcs': [{'kc_code': 'ai_product_canvas'}]},
}}


def write_csv(path, rows):
    header = 'chunk_id,lesson_id,kc_code,confirmed\n'
    path.write_text(header + ''.join(','.join(row) + '\n' for row in rows), encoding='utf-8')


def test_catalog_lists_every_lesson_kc_pair_sorted():
    assert kc_catalog(SNAPSHOT_V2) == [
        {'lesson_id': 'program-day05:product', 'kc_code': 'ai_product_canvas'},
        {'lesson_id': 'program-day07:retrieval', 'kc_code': 'chunk_size_tradeoff'},
        {'lesson_id': 'program-day07:retrieval', 'kc_code': 'context_window_contents'},
        {'lesson_id': 'program-day07:retrieval', 'kc_code': 'program-day07:retrieval:module-1'},
    ]


def test_propose_picks_best_matching_kc_skips_module_kcs_and_leaves_unconfirmed():
    rows = propose_mapping(chunk_notes(NOTES, 'notes/day07'), kc_catalog(SNAPSHOT_V2))
    assert rows[0]['chunk_id'] == 'notes/day07:1'
    assert (rows[0]['lesson_id'], rows[0]['kc_code']) == ('program-day07:retrieval', 'chunk_size_tradeoff')
    assert all(row['confirmed'] == '' and ':module-' not in row['kc_code'] for row in rows)
    assert all(':module-' not in row['alternatives'] for row in rows)


def test_proposal_round_trips_through_csv_and_unconfirmed_rows_are_ignored(tmp_path):
    path = tmp_path / 'kb_mapping.csv'
    write_mapping(propose_mapping(chunk_notes(NOTES, 'notes/day07'), kc_catalog(SNAPSHOT_V2)), path)
    assert load_mapping(path, kc_catalog(SNAPSHOT_V2)) == {}


def test_load_mapping_keeps_only_confirmed_rows(tmp_path):
    path = tmp_path / 'm.csv'
    write_csv(path, [('notes/day07:1', 'program-day07:retrieval', 'chunk_size_tradeoff', 'yes'),
                     ('notes/day07:2', 'program-day07:retrieval', 'context_window_contents', ''),
                     ('notes/day07:3', 'program-day05:product', 'ai_product_canvas', 'no')])
    assert load_mapping(path, kc_catalog(SNAPSHOT_V2)) == {
        'notes/day07:1': {'lesson_id': 'program-day07:retrieval', 'kc_code': 'chunk_size_tradeoff'}}


def test_load_mapping_rejects_kc_outside_catalog(tmp_path):
    path = tmp_path / 'm.csv'
    write_csv(path, [('notes/day07:1', 'program-day05:product', 'chunk_size_tradeoff', 'yes')])
    with pytest.raises(ValueError, match='không có trong danh mục'):
        load_mapping(path, kc_catalog(SNAPSHOT_V2))


def test_load_mapping_rejects_missing_columns(tmp_path):
    path = tmp_path / 'm.csv'
    path.write_text('chunk_id,lesson_id\nx,y\n', encoding='utf-8')
    with pytest.raises(ValueError, match='thiếu cột'):
        load_mapping(path, kc_catalog(SNAPSHOT_V2))


def test_to_documents_maps_confirmed_chunks_as_unapproved_and_counts_skipped():
    chunks = chunk_notes(NOTES, 'notes/day07') + chunk_quiz(QUIZ, 'quiz/day04')
    target = {'lesson_id': 'program-day07:retrieval', 'kc_code': 'chunk_size_tradeoff'}
    docs, skipped = to_documents(chunks, {'notes/day07:1': target})
    assert [d['id'] for d in docs] == ['notes/day07:1']
    assert docs[0]['approved'] is False and docs[0]['kc_code'] == 'chunk_size_tradeoff'
    assert skipped == 2


def test_unapproved_documents_are_not_retrievable():
    target = {'lesson_id': 'L7', 'kc_code': 'K'}
    docs, _ = to_documents(chunk_notes(NOTES, 'notes/day07'), {'notes/day07:1': target, 'notes/day07:2': target})
    assert retrieve(docs, 'L7', 'K', 'chunk truy xuất') == []


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def make_store(handler, clock=None):
    transport = httpx.MockTransport(handler)
    return KnowledgeStore('https://example.supabase.co', 'service-key-fake',
                          client_factory=lambda **kw: httpx.Client(transport=transport, **kw),
                          clock=clock or FakeClock(), now=lambda: datetime(2026, 11, 28, tzinfo=timezone.utc))


def test_approved_documents_queries_only_approved_columns_and_caches_until_ttl():
    calls, clock = [], FakeClock()

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[{'id': 'a', 'lesson_id': 'L1', 'kc_code': 'K', 'text': 't', 'approved': True}])

    store = make_store(handler, clock)
    assert store.approved_documents()[0]['id'] == 'a'
    store.approved_documents()
    assert len(calls) == 1
    query = dict(calls[0].url.params)
    assert query['approved'] == 'eq.true' and query['select'] == 'id,lesson_id,kc_code,text,approved'
    assert 'limit' in query
    assert calls[0].headers['authorization'] == 'Bearer service-key-fake'
    clock.now = CACHE_TTL_SECONDS + 1
    store.approved_documents()
    assert len(calls) == 2


@pytest.mark.parametrize('response', [httpx.Response(500), httpx.Response(200, text='not json'),
                                      httpx.Response(200, json={'a': 1})])
def test_approved_documents_raises_repository_error_on_bad_response(response):
    with pytest.raises(RepositoryError):
        make_store(lambda request: response).approved_documents()


def test_network_error_does_not_leak_url_or_key():
    def handler(request):
        raise httpx.ConnectError('boom https://example.supabase.co service-key-fake')

    with pytest.raises(RepositoryError) as error:
        make_store(handler).approved_documents()
    assert 'service-key-fake' not in str(error.value) and error.value.__cause__ is None


def test_upsert_batches_never_sends_approved_and_invalidates_cache():
    sent = []

    def handler(request):
        if request.method == 'POST':
            sent.append(json.loads(request.content))
            return httpx.Response(201)
        return httpx.Response(200, json=[])

    store = make_store(handler)
    store.approved_documents()
    docs = [{'id': f'd{i}', 'lesson_id': 'L', 'kc_code': 'K', 'text': 't', 'source': 's', 'approved': True}
            for i in range(450)]
    assert store.upsert_documents(docs) == 450
    assert [len(batch) for batch in sent] == [200, 200, 50]
    assert all('approved' not in row and row['updated_at'].startswith('2026-11-28') for batch in sent for row in batch)
    assert store._cache is None
