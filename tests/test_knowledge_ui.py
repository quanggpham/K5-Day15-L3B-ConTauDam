import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from codebase.backend.main import app
from codebase.backend.api import knowledge
from codebase.backend.rag.ingestion import extract_chunks
from codebase.backend.security.auth import require_coach


def test_extract_markdown_and_reject_scan():
    assert [x['text'] for x in extract_chunks('b.md', 'Một đoạn\n\nHai đoạn'.encode())] == ['Một đoạn', 'Hai đoạn']
    pdf = PdfWriter()
    pdf.add_blank_page(width=100, height=100)
    data = io.BytesIO()
    pdf.write(data)
    with pytest.raises(ValueError, match='scan'):
        extract_chunks('scan.pdf', data.getvalue())
    with pytest.raises(ValueError):
        extract_chunks('test.exe', b'content')


def test_upload_requires_permission_and_creates_pending_only(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: [{'lesson_id': 'L1', 'kc_code': 'K1'}])
    writes = []
    monkeypatch.setattr(knowledge, 'request', lambda *args, **kwargs: writes.append((args, kwargs)) or [])
    client = TestClient(app)
    files = {'file': ('notes.md', b'Hello lesson', 'text/markdown')}
    try:
        denied = client.post('/api/knowledge/upload', data={'lesson_id': 'L1', 'source': 'allowed', 'permission_confirmed': 'false'}, files=files)
        assert denied.status_code == 422 and not writes
        result = client.post('/api/knowledge/upload', data={'lesson_id': 'L1', 'source': 'allowed', 'permission_confirmed': 'true'}, files=files)
        assert result.status_code == 200 and result.json()['chunks'] == 1
        assert writes[0][0][2]['p_rows'][0]['kc_code'] == 'K1' and 'approved' not in writes[0][0][2]['p_rows'][0]
        assert writes[0][1]['table'] == 'rpc/ingest_knowledge_document'
    finally:
        app.dependency_overrides.clear()


def test_edit_validates_catalog_and_version_conflicts(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: [{'lesson_id': 'L1', 'kc_code': 'K1'}])
    monkeypatch.setattr(knowledge, 'request', lambda *args: [])
    client = TestClient(app)
    try:
        body = {'version': 1, 'lesson_id': 'L1', 'kc_code': 'bad', 'text': 'Nội dung', 'source': 'Nguồn'}
        assert client.post('/api/knowledge/edit?document_id=notes%2Fday01%3A1', json=body).status_code == 422
        body['kc_code'] = 'K1'
        assert client.post('/api/knowledge/edit?document_id=notes%2Fday01%3A1', json=body).status_code == 409
        assert client.post('/api/knowledge/approve?document_id=notes%2Fday01%3A1', json={'version': 1}).status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_search_only_returns_approved_matching_documents(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: [{'lesson_id': 'L1', 'kc_code': 'K1'}])
    monkeypatch.setattr(knowledge, 'request', lambda *args: [
        {'id': 'a', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'bài học', 'approved': True},
        {'id': 'b', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'bài học', 'approved': False},
        {'id': 'c', 'lesson_id': 'L2', 'kc_code': 'K1', 'text': 'bài học', 'approved': True},
    ])
    try:
        response = TestClient(app).get('/api/knowledge/search', params={'lesson_id': 'L1', 'kc_code': 'K1', 'query': 'bài'})
        assert response.status_code == 200 and [row['id'] for row in response.json()] == ['a']
    finally:
        app.dependency_overrides.clear()


def test_extract_pdf_with_text():
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    font = writer._add_object(DictionaryObject({NameObject('/Type'): NameObject('/Font'),
        NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')}))
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
    content = DecodedStreamObject()
    content.set_data(b'BT /F1 12 Tf 10 100 Td (Lesson content) Tj ET')
    page[NameObject('/Contents')] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    assert 'Lesson content' in extract_chunks('lesson.pdf', output.getvalue())[0]['text']


def test_knowledge_rejects_unauthenticated():
    assert TestClient(app).get('/api/knowledge').status_code == 401


def test_list_paginated_and_excludes_retired(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    calls = []
    monkeypatch.setattr(knowledge, 'request', lambda method, params: calls.append(params) or [{'id': str(i)} for i in range(101)])
    try:
        response = TestClient(app).get('/api/knowledge', params={'page': 2})
        assert response.status_code == 200
        assert len(response.json()['items']) == 100 and response.json()['has_more'] is True
        assert calls[0]['offset'] == '200' and calls[0]['is_current'] == 'eq.true'
    finally:
        app.dependency_overrides.clear()


def test_search_fetches_multiple_pages(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: [{'lesson_id': 'L1', 'kc_code': 'K1'}])
    calls = []
    def fake_request(method, params):
        calls.append(params)
        count = 200 if params['offset'] == '0' else 1
        return [{'id': str(int(params['offset']) + i), 'lesson_id': 'L1', 'kc_code': 'K1',
                 'text': 'Bài học', 'approved': True} for i in range(count)]
    monkeypatch.setattr(knowledge, 'request', fake_request)
    try:
        response = TestClient(app).get('/api/knowledge/search', params={'lesson_id': 'L1', 'kc_code': 'K1', 'query': 'bài'})
        assert response.status_code == 200 and len(response.json()) == 3
        assert [call['offset'] for call in calls] == ['0', '200']
        assert all(call['is_current'] == 'eq.true' for call in calls)
    finally:
        app.dependency_overrides.clear()


def test_search_returns_no_evidence_when_query_has_no_matching_terms(monkeypatch):
    app.dependency_overrides[require_coach] = lambda: {'id': '123'}
    monkeypatch.setattr(knowledge, 'catalog', lambda: [{'lesson_id': 'L1', 'kc_code': 'K1'}])
    monkeypatch.setattr(knowledge, 'request', lambda *args: [
        {'id': 'a', 'lesson_id': 'L1', 'kc_code': 'K1', 'text': 'bài học', 'approved': True}])
    try:
        response = TestClient(app).get('/api/knowledge/search', params={'lesson_id': 'L1', 'kc_code': 'K1', 'query': 'khôngliênquan'})
        assert response.status_code == 200 and response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_bulk_apply_requires_explicit_source_rights(capsys):
    from scripts.ingest_kb import main
    with pytest.raises(SystemExit):
        main(['--files', '.', '--mapping', 'mapping.csv', '--apply'])
    assert '--confirm-rights' in capsys.readouterr().err


def test_bulk_cli_outputs_utf8_on_windows_with_legacy_encoding(tmp_path):
    import os
    import subprocess
    import sys
    (tmp_path / 'lesson.md').write_text('Synthetic lesson content', encoding='utf-8')
    env = {**os.environ, 'PYTHONIOENCODING': 'cp1252'}
    result = subprocess.run([sys.executable, 'scripts/ingest_kb.py', '--files', str(tmp_path)],
                            env=env, capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0
    assert 'đoạn' in result.stdout
