import json
import math

import httpx
import pytest
from fastapi.testclient import TestClient

from codebase.backend.api import knowledge
from codebase.backend.api.run_repository import RepositoryError
from codebase.backend.main import app
from codebase.backend.rag.embedding import (EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, to_vector_literal,
                                            validate_embeddings)
from codebase.backend.rag.kb_mapping import load_mapping, write_mapping
from codebase.backend.rag.store import EMBEDDING_BATCH_SIZE, KnowledgeStore
from codebase.backend.security.auth import require_coach
from scripts import load_kb_embeddings
from scripts.export_kb_chunks import build_export_rows

CATALOG = [{'lesson_id': 'L1', 'kc_code': 'K1'}, {'lesson_id': 'L1', 'kc_code': 'K2'}]


def vector(value=0.1):
    return [value] * EMBEDDING_DIMENSIONS


def embedding_row(chunk_id='a', **overrides):
    return {'id': chunk_id, 'model': EMBEDDING_MODEL, 'embedding': vector(), **overrides}


def chunk(chunk_id='a', source='notes/day01', **overrides):
    return {'id': chunk_id, 'source': source, 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'nội dung', **overrides}


def make_store(handler):
    transport = httpx.MockTransport(handler)
    return KnowledgeStore('https://example.supabase.co', 'service-key-fake',
                          client_factory=lambda **kw: httpx.Client(transport=transport, **kw))


# --- validate_embeddings -------------------------------------------------------------------------

def test_validate_embeddings_returns_vectors_by_id():
    result = validate_embeddings([embedding_row('a'), embedding_row('b', embedding=vector(0.2))], {'a', 'b'})
    assert set(result) == {'a', 'b'} and result['b'][0] == 0.2 and len(result['a']) == EMBEDDING_DIMENSIONS


@pytest.mark.parametrize('row, reason', [
    (embedding_row(model='other/model'), 'model'),
    (embedding_row('zzz'), 'không có trong file chunk'),
    (embedding_row(embedding=[0.1] * (EMBEDDING_DIMENSIONS - 1)), 'chiều'),
    (embedding_row(embedding='[0.1]'), 'chiều'),
    (embedding_row(embedding=[math.nan] + vector()[1:]), 'hữu hạn'),
    (embedding_row(embedding=[math.inf] + vector()[1:]), 'hữu hạn'),
    (embedding_row(embedding=[True] + vector()[1:]), 'hữu hạn'),
    (embedding_row(embedding=['0.1'] + vector()[1:]), 'hữu hạn'),
])
def test_validate_embeddings_rejects_invalid_row(row, reason):
    with pytest.raises(ValueError, match=reason):
        validate_embeddings([row], {'a'})


def test_validate_embeddings_rejects_duplicate_id():
    with pytest.raises(ValueError, match='lặp'):
        validate_embeddings([embedding_row('a'), embedding_row('a')], {'a'})


def test_validate_embeddings_rejects_missing_chunk():
    with pytest.raises(ValueError, match='thiếu embedding cho 1 đoạn'):
        validate_embeddings([embedding_row('a')], {'a', 'b'})


def test_vector_literal_uses_pgvector_text_format():
    assert to_vector_literal([1, 0.5, -2.25]) == '[1.0,0.5,-2.25]'


# --- export ----------------------------------------------------------------------------------------

def write_rows(tmp_path, rows):
    path = tmp_path / 'map.csv'
    write_mapping([{'chunk_id': cid, 'lesson_id': 'L1', 'kc_code': kc, 'confirmed': confirmed, 'score': '',
                    'alternatives': '', 'preview': ''} for cid, kc, confirmed in rows], path)
    return path


def test_load_mapping_include_unconfirmed_keeps_proposals(tmp_path):
    path = write_rows(tmp_path, [('a', 'K1', 'yes'), ('b', 'K2', '')])
    assert set(load_mapping(path, CATALOG)) == {'a'}
    assert load_mapping(path, CATALOG, include_unconfirmed=True)['b'] == {'lesson_id': 'L1', 'kc_code': 'K2'}


def test_load_mapping_include_unconfirmed_still_rejects_unknown_kc(tmp_path):
    path = write_rows(tmp_path, [('a', 'K9', '')])
    with pytest.raises(ValueError, match='không có trong danh mục'):
        load_mapping(path, CATALOG, include_unconfirmed=True)


def test_build_export_rows_applies_mapping_and_keeps_only_export_fields():
    chunks = [{'id': 'a', 'text': 'văn bản', 'source': 'notes/day01'}]
    rows = build_export_rows(chunks, {'a': {'lesson_id': 'L1', 'kc_code': 'K2'}})
    assert rows == [{'id': 'a', 'source': 'notes/day01', 'lesson_id': 'L1', 'kc_code': 'K2', 'text': 'văn bản'}]


def test_build_export_rows_rejects_chunk_without_mapping():
    with pytest.raises(ValueError, match='1 đoạn chưa có dòng ánh xạ'):
        build_export_rows([{'id': 'a', 'text': 't', 'source': 's'}], {})


def test_build_export_rows_rejects_duplicate_chunk_ids():
    chunks = [{'id': 'a', 'text': 't', 'source': 's'}] * 2
    with pytest.raises(ValueError, match='lặp'):
        build_export_rows(chunks, {'a': {'lesson_id': 'L1', 'kc_code': 'K1'}})


# --- KnowledgeStore RPC ----------------------------------------------------------------------------

def test_ingest_document_calls_rpc_with_only_document_fields():
    seen = []

    def handler(request):
        seen.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json=1)

    assert make_store(handler).ingest_document('notes/day01', [chunk(approved=True, extra='x')]) == 1
    path, body = seen[0]
    assert path == '/rest/v1/rpc/ingest_knowledge_document'
    assert body == {'p_key': 'notes/day01', 'p_actor': None, 'p_rows': [
        {'id': 'a', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'nội dung', 'source': 'notes/day01'}]}


def test_set_embeddings_sends_batches_and_sums_updated_rows():
    batches = []

    def handler(request):
        body = json.loads(request.content)
        assert request.url.path == '/rest/v1/rpc/set_knowledge_embeddings' and body['p_model'] == EMBEDDING_MODEL
        batches.append(len(body['p_rows']))
        return httpx.Response(200, json=len(body['p_rows']))

    vectors = {f'id{i:03d}': '[0.1]' for i in range(EMBEDDING_BATCH_SIZE + 1)}
    assert make_store(handler).set_embeddings(EMBEDDING_MODEL, vectors) == EMBEDDING_BATCH_SIZE + 1
    assert batches == [EMBEDDING_BATCH_SIZE, 1]


def test_match_documents_returns_rpc_rows():
    def handler(request):
        assert json.loads(request.content) == {'p_embedding': '[0.1]', 'p_lesson_id': 'L1', 'p_kc_code': 'K1', 'p_limit': 3}
        return httpx.Response(200, json=[{'id': 'a'}])

    assert make_store(handler).match_documents('[0.1]', 'L1', 'K1', 3) == [{'id': 'a'}]


@pytest.mark.parametrize('response, code', [
    (httpx.Response(400, json={'message': 'expected 384 dimensions'}), 'supabase_status_400'),
    (httpx.Response(200, content=b'not json'), 'supabase_bad_json'),
])
def test_rpc_errors_raise_repository_error(response, code):
    with pytest.raises(RepositoryError, match=code):
        make_store(lambda request: response).set_embeddings(EMBEDDING_MODEL, {'a': '[0.1]'})


def test_match_documents_rejects_non_list_response():
    with pytest.raises(RepositoryError, match='supabase_bad_shape'):
        make_store(lambda request: httpx.Response(200, json={'id': 'a'})).match_documents('[0.1]', 'L1', 'K1', 3)


def test_rpc_network_error_does_not_leak_details():
    def handler(request):
        raise httpx.ConnectError('boom service-key-fake')

    with pytest.raises(RepositoryError) as error:
        make_store(handler).ingest_document('k', [chunk()])
    assert str(error.value) == 'supabase_unreachable' and error.value.__cause__ is None


# --- load_kb_embeddings script ---------------------------------------------------------------------

class FakeStore:
    def __init__(self, url, key):
        self.ingested, self.embedded = [], {}

    def ingest_document(self, key, rows):
        self.ingested.append((key, [r['id'] for r in rows]))
        return len(rows)

    def set_embeddings(self, model, vectors):
        self.embedded = vectors
        return len(vectors)


def write_inputs(tmp_path, chunks, embeddings):
    chunks_path, embeddings_path = tmp_path / 'chunks.jsonl', tmp_path / 'emb.jsonl'
    chunks_path.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in chunks), encoding='utf-8')
    embeddings_path.write_text(''.join(json.dumps(e) + '\n' for e in embeddings), encoding='utf-8')
    return ['--chunks', str(chunks_path), '--embeddings', str(embeddings_path)]


def test_load_script_dry_run_validates_without_writing(tmp_path, capsys):
    stores = []
    args = write_inputs(tmp_path, [chunk('a')], [embedding_row('a')])
    assert load_kb_embeddings.main(args, store_factory=lambda *a: stores.append(a)) == 0
    assert stores == [] and 'Dry-run' in capsys.readouterr().out


def test_load_script_apply_requires_rights_confirmation(tmp_path):
    args = write_inputs(tmp_path, [chunk('a')], [embedding_row('a')])
    with pytest.raises(SystemExit):
        load_kb_embeddings.main(args + ['--apply'])


def test_load_script_rejects_invalid_embeddings_before_writing(tmp_path):
    stores = []
    args = write_inputs(tmp_path, [chunk('a'), chunk('b')], [embedding_row('a')])
    with pytest.raises(ValueError, match='thiếu embedding'):
        load_kb_embeddings.main(args + ['--apply', '--confirm-rights'], store_factory=lambda *a: stores.append(a))
    assert stores == []


def test_load_script_apply_ingests_per_source_then_embeds(tmp_path, monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'service-key-fake')
    created = []

    def factory(url, key):
        created.append(FakeStore(url, key))
        return created[-1]

    chunks = [chunk('b', 'quiz/day01'), chunk('a', 'notes/day01'), chunk('c', 'notes/day01')]
    args = write_inputs(tmp_path, chunks, [embedding_row(c['id']) for c in chunks])
    assert load_kb_embeddings.main(args + ['--apply', '--confirm-rights'], store_factory=factory) == 0
    store = created[0]
    assert store.ingested == [('notes/day01', ['a', 'c']), ('quiz/day01', ['b'])]
    assert set(store.embedded) == {'a', 'b', 'c'} and store.embedded['a'].startswith('[0.1,')


def test_load_script_apply_without_service_key_returns_error(tmp_path, monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', '')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', '')
    monkeypatch.setattr(load_kb_embeddings, 'load_dotenv', lambda: None)
    args = write_inputs(tmp_path, [chunk('a')], [embedding_row('a')])
    assert load_kb_embeddings.main(args + ['--apply', '--confirm-rights'], store_factory=FakeStore) == 2


def test_group_by_source_rejects_oversized_document():
    with pytest.raises(ValueError, match='hơn 500 đoạn'):
        load_kb_embeddings.group_by_source([chunk(f'c{i}') for i in range(501)])


# --- /api/knowledge/search -------------------------------------------------------------------------

@pytest.fixture
def coach_client(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: CATALOG)
    yield TestClient(app)
    app.dependency_overrides.clear()


def search(client):
    return client.get('/api/knowledge/search', params={'lesson_id': 'L1', 'kc_code': 'K1', 'query': 'agent loop'})


def test_search_uses_vector_rpc_when_embedder_available(coach_client, monkeypatch):
    calls = []
    queries = []
    monkeypatch.setattr(knowledge, 'query_embedder', lambda: lambda q: queries.append(q) or [0.5] * 3)

    def fake_request(method, params=None, body=None, prefer=None, table='knowledge_documents'):
        calls.append((method, table, body))
        return [{'id': 'a', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 't', 'source': 's', 'approved': True,
                 'version': 1, 'similarity': 0.9}]

    monkeypatch.setattr(knowledge, 'request', fake_request)
    response = search(coach_client)
    assert response.status_code == 200 and [row['id'] for row in response.json()] == ['a']
    assert queries == ['agent loop']
    assert calls == [('POST', 'rpc/match_knowledge_documents',
                      {'p_embedding': '[0.5,0.5,0.5]', 'p_lesson_id': 'L1', 'p_kc_code': 'K1', 'p_limit': 3})]


def test_search_falls_back_to_bm25_when_no_vector_match(coach_client, monkeypatch):
    monkeypatch.setattr(knowledge, 'query_embedder', lambda: lambda q: [0.5] * 3)
    tables = []

    def fake_request(method, params=None, body=None, prefer=None, table='knowledge_documents'):
        tables.append(table)
        if table.startswith('rpc/'):
            return []
        return [{'id': 'b', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'agent loop cơ bản', 'approved': True}]

    monkeypatch.setattr(knowledge, 'request', fake_request)
    response = search(coach_client)
    assert response.status_code == 200 and [row['id'] for row in response.json()] == ['b']
    assert tables == ['rpc/match_knowledge_documents', 'knowledge_documents']


def test_search_skips_vector_rpc_without_embedder(coach_client, monkeypatch):
    tables = []

    def fake_request(method, params=None, body=None, prefer=None, table='knowledge_documents'):
        tables.append(table)
        return []

    monkeypatch.setattr(knowledge, 'request', fake_request)
    assert search(coach_client).json() == [] and tables == ['knowledge_documents']
