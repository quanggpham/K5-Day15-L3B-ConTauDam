-- Forward-only, expand step. Lesson KB thêm embedding (pgvector) cho truy xuất ngữ nghĩa; BM25 vẫn là fallback.
-- Model: intfloat/multilingual-e5-small (384 chiều, vector đã chuẩn hoá) -> so khớp bằng cosine.
-- Vector được tính ngoài DB (Kaggle/local) rồi nạp bằng scripts/load_kb_embeddings.py.
-- Chỉ service role gọi được hàm tìm kiếm/nạp; tìm kiếm chỉ trả đoạn approved + is_current.
-- DOWN:
--   drop function public.set_knowledge_embeddings(text, jsonb);
--   drop function public.match_knowledge_documents(extensions.vector, text, text, integer);
--   drop trigger knowledge_document_embedding_reset on public.knowledge_documents;
--   drop function public.knowledge_document_embedding_reset();
--   drop index public.knowledge_documents_embedding_idx;
--   alter table public.knowledge_documents drop column embedding_model, drop column embedding;

create extension if not exists vector with schema extensions;

alter table public.knowledge_documents add column embedding extensions.vector(384);
alter table public.knowledge_documents add column embedding_model text
  check (embedding_model is null or length(embedding_model) between 1 and 128);
alter table public.knowledge_documents add constraint knowledge_documents_embedding_pair_check
  check ((embedding is null) = (embedding_model is null));

create index knowledge_documents_embedding_idx on public.knowledge_documents
  using hnsw (embedding extensions.vector_cosine_ops) where approved and is_current;

-- Sửa nội dung đoạn thì vector cũ không còn đúng: xoá để nạp lại, không trả kết quả theo nội dung cũ.
create function public.knowledge_document_embedding_reset() returns trigger language plpgsql set search_path = '' as $$
begin
  if new.text is distinct from old.text and new.embedding::text is not distinct from old.embedding::text then
    new.embedding := null;
    new.embedding_model := null;
  end if;
  return new;
end $$;
create trigger knowledge_document_embedding_reset before update on public.knowledge_documents
for each row execute function public.knowledge_document_embedding_reset();

create function public.match_knowledge_documents(
  p_embedding extensions.vector(384), p_lesson_id text, p_kc_code text, p_limit integer default 3)
returns table (id text, lesson_id text, kc_code text, "text" text, source text, approved boolean, version integer,
               similarity double precision)
language sql stable security definer set search_path = '' as $$
  select d.id, d.lesson_id, d.kc_code, d.text, d.source, d.approved, d.version,
         1 - (d.embedding operator(extensions.<=>) p_embedding)
  from public.knowledge_documents d
  where d.approved and d.is_current and d.embedding is not null
    and d.lesson_id = p_lesson_id and d.kc_code = p_kc_code
  order by d.embedding operator(extensions.<=>) p_embedding, d.id
  limit least(greatest(coalesce(p_limit, 3), 0), 20);
$$;
revoke all on function public.match_knowledge_documents(extensions.vector, text, text, integer) from public, anon, authenticated;
grant execute on function public.match_knowledge_documents(extensions.vector, text, text, integer) to service_role;

-- Nạp vector theo lô bằng một câu lệnh; chỉ cập nhật đoạn đang dùng. Không đổi text nên không sinh lịch sử.
create function public.set_knowledge_embeddings(p_model text, p_rows jsonb) returns integer
language plpgsql security definer set search_path = '' as $$
declare updated_rows integer;
begin
  if p_model is null or length(p_model) not between 1 and 128 or jsonb_typeof(p_rows) is distinct from 'array'
     or jsonb_array_length(p_rows) not between 1 and 500 then
    raise exception 'invalid embeddings';
  end if;
  update public.knowledge_documents d
  set embedding = (x->>'embedding')::extensions.vector(384), embedding_model = p_model
  from jsonb_array_elements(p_rows) x
  where d.id = x->>'id' and d.is_current;
  get diagnostics updated_rows = row_count;
  return updated_rows;
end $$;
revoke all on function public.set_knowledge_embeddings(text, jsonb) from public, anon, authenticated;
grant execute on function public.set_knowledge_embeddings(text, jsonb) to service_role;
