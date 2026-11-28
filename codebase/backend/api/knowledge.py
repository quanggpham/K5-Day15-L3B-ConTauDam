"""Quản lý các đoạn bài giảng dùng chung; chỉ backend giữ service role."""
import os
import re
import hashlib
from datetime import datetime, timezone
from pathlib import PurePath

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from codebase.backend.analytics.snapshot import read_snapshot_v2
from codebase.backend.rag.ingestion import MAX_BYTES, extract_chunks
from codebase.backend.rag.embedding import load_query_embedder, to_vector_literal
from codebase.backend.rag.kb_mapping import kc_catalog, propose_mapping
from codebase.backend.rag.retrieval import retrieve
from codebase.backend.security.auth import require_coach

router = APIRouter(prefix='/api/knowledge', tags=['knowledge'])
COLUMNS = 'id,lesson_id,kc_code,text,source,approved,version,reviewed_by,reviewed_at,updated_by,updated_at'
SEARCH_LIMIT = 3
# Thay được trong test; trả None khi chưa cài extra `embed` -> tìm bằng BM25.
query_embedder = load_query_embedder


def catalog():
    snapshot = read_snapshot_v2()
    if snapshot is None:
        raise HTTPException(503, 'Chưa có danh mục bài và KC.')
    return kc_catalog(snapshot)


def request(method, params=None, body=None, prefer=None, table="knowledge_documents"):
    url, key = os.getenv('SUPABASE_URL', '').rstrip('/'), os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
    if not url or not key:
        raise HTTPException(503, 'Chưa cấu hình kho KB.')
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    if prefer:
        headers['Prefer'] = prefer
    try:
        with httpx.Client(timeout=20) as client:
            response = client.request(method, f'{url}/rest/v1/{table}', params=params, json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else []
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'Không thể truy cập kho KB.') from None


class Edit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)
    lesson_id: str = Field(min_length=1, max_length=64)
    kc_code: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=8000)
    source: str = Field(min_length=1, max_length=256)


class Approval(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)


def update(document_id, version, body):
    rows = request('PATCH', {'id': f'eq.{document_id}', 'version': f'eq.{version}', 'is_current': 'eq.true', 'select': COLUMNS}, body, 'return=representation')
    if not rows:
        raise HTTPException(409, 'Đoạn đã thay đổi hoặc không tồn tại; hãy tải lại.')
    return rows[0]


@router.get('/catalog')
def get_catalog(user: dict = Depends(require_coach)):
    return catalog()


@router.get('')
def list_documents(page: int = Query(default=0, ge=0, le=10000), user: dict = Depends(require_coach)):
    rows = request('GET', {'select': COLUMNS, 'is_current': 'eq.true', 'order': 'updated_at.desc,id.asc', 'limit': '101', 'offset': str(page * 100)})
    return {'items': rows[:100], 'has_more': len(rows) > 100}


@router.get('/search')
def search(lesson_id: str, kc_code: str, query: str, user: dict = Depends(require_coach)):
    if not query.strip() or len(query) > 500:
        raise HTTPException(422, 'Câu truy vấn phải có từ 1 đến 500 ký tự.')
    if (lesson_id, kc_code) not in {(row['lesson_id'], row['kc_code']) for row in catalog()}:
        raise HTTPException(422, 'Bài và KC không thuộc danh mục.')
    embed = query_embedder()
    if embed is not None:
        matches = request('POST', body={'p_embedding': to_vector_literal(embed(query)), 'p_lesson_id': lesson_id,
                                        'p_kc_code': kc_code, 'p_limit': SEARCH_LIMIT},
                          table='rpc/match_knowledge_documents')
        # Rỗng khi các đoạn đã duyệt chưa được nạp vector: dùng BM25 để vẫn có căn cứ.
        if matches:
            return matches
    documents = []
    for offset in range(0, 5001, 200):
        batch = request('GET', {'select': COLUMNS, 'lesson_id': f'eq.{lesson_id}', 'kc_code': f'eq.{kc_code}',
                                'approved': 'eq.true', 'is_current': 'eq.true', 'order': 'id.asc',
                                'limit': '200', 'offset': str(offset)})
        documents.extend(batch)
        if len(documents) > 5000:
            raise HTTPException(503, 'KB quá lớn để truy xuất an toàn.')
        if len(batch) < 200:
            terms = set(re.findall(r'\w+', query.casefold()))
            relevant = [doc for doc in documents if isinstance(doc.get('text'), str)
                        and terms.intersection(re.findall(r'\w+', doc['text'].casefold()))]
            return retrieve(relevant, lesson_id, kc_code, query)
    raise HTTPException(503, 'KB quá lớn để truy xuất an toàn.')


@router.post('/upload')
async def upload(file: UploadFile = File(...), lesson_id: str = Form(...), source: str = Form(...),
                 permission_confirmed: bool = Form(...), user: dict = Depends(require_coach)):
    if not permission_confirmed:
        raise HTTPException(422, 'Cần xác nhận quyền sử dụng tài liệu.')
    source = source.strip()
    if not source or len(source) > 256:
        raise HTTPException(422, 'Nguồn tài liệu phải có từ 1 đến 256 ký tự.')
    targets = [row for row in catalog() if row['lesson_id'] == lesson_id]
    if not targets:
        raise HTTPException(422, 'Bài học không có trong danh mục.')
    data = await file.read(MAX_BYTES + 1)
    try:
        chunks = extract_chunks(file.filename or '', data)
        filename = PurePath((file.filename or '').replace('\\', '/')).name
        identity = hashlib.sha256((lesson_id + '\0' + source + '\0' + filename).encode()).hexdigest()
        chunks = [{**chunk, 'id': identity + ':' + chunk['id']} for chunk in chunks]
        proposals = propose_mapping(chunks, targets)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    rows = [{'id': c['id'], 'lesson_id': lesson_id, 'kc_code': m['kc_code'], 'text': c['text'],
             'source': source, 'updated_by': user['id']} for c, m in zip(chunks, proposals)]
    request('POST', None, {'p_key': identity, 'p_rows': rows, 'p_actor': user['id']}, table='rpc/ingest_knowledge_document')
    return {'chunks': len(rows), 'message': 'Đã xử lý; các đoạn mới chờ duyệt.'}


@router.get('/history')
def history(document_id: str, user: dict = Depends(require_coach)):
    return request('GET', {'document_id': f'eq.{document_id}', 'select': 'version,snapshot,changed_by,changed_at',
                           'order': 'id.desc', 'limit': '100'}, table='knowledge_document_history')


@router.post('/edit')
def edit(document_id: str, body: Edit, user: dict = Depends(require_coach)):
    if (body.lesson_id, body.kc_code) not in {(row['lesson_id'], row['kc_code']) for row in catalog()}:
        raise HTTPException(422, 'Bài và KC không thuộc danh mục.')
    if not body.text.strip() or not body.source.strip():
        raise HTTPException(422, 'Nội dung và nguồn không được để trống.')
    return update(document_id, body.version, {'lesson_id': body.lesson_id, 'kc_code': body.kc_code,
                  'text': body.text, 'source': body.source, 'updated_by': user['id'],
                  'updated_at': datetime.now(timezone.utc).isoformat()})


@router.post('/approve')
def approve(document_id: str, body: Approval, user: dict = Depends(require_coach)):
    return update(document_id, body.version, {'approved': True, 'reviewed_by': user['id'], 'updated_by': user['id'],
                  'reviewed_at': datetime.now(timezone.utc).isoformat()})
