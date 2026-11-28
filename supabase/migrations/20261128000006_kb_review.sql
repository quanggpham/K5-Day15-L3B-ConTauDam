-- Giữ lịch sử trước khi thay đổi; chỉ service role được ghi qua backend.
alter table public.knowledge_documents add column document_key text;
alter table public.knowledge_documents add column is_current boolean not null default true;
alter table public.knowledge_documents add column version integer not null default 1;
alter table public.knowledge_documents add column reviewed_by uuid references auth.users(id) on delete set null;
alter table public.knowledge_documents add column reviewed_at timestamptz;
alter table public.knowledge_documents add column updated_by uuid references auth.users(id) on delete set null;
create table public.knowledge_document_history (
  id bigint generated always as identity primary key,
  document_id text not null,
  version integer not null,
  snapshot jsonb not null,
  changed_by uuid references auth.users(id) on delete set null,
  changed_at timestamptz not null default now()
);
alter table public.knowledge_document_history enable row level security;
revoke all on public.knowledge_document_history from anon, authenticated;
grant select, insert, update on public.knowledge_documents to service_role;
grant select on public.knowledge_document_history to service_role;
create function public.knowledge_document_change() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if (new.text, new.lesson_id, new.kc_code, new.source, new.approved, new.is_current) is distinct from (old.text, old.lesson_id, old.kc_code, old.source, old.approved, old.is_current) then
    insert into public.knowledge_document_history(document_id, version, snapshot, changed_by) values (old.id, old.version, to_jsonb(old), new.updated_by);
    new.version := old.version + 1;
    if (new.text, new.lesson_id, new.kc_code, new.source, new.is_current) is distinct from (old.text, old.lesson_id, old.kc_code, old.source, old.is_current) then
      new.approved := false;
      new.reviewed_by := null;
      new.reviewed_at := null;
    end if;
  end if;
  return new;
end $$;
create trigger knowledge_document_change before update on public.knowledge_documents
for each row execute function public.knowledge_document_change();

-- Nạp một tài liệu là một transaction; bản cũ không còn được duyệt hoặc truy xuất.
create function public.ingest_knowledge_document(p_key text, p_rows jsonb, p_actor uuid) returns integer
language plpgsql security definer set search_path = '' as $$
declare item jsonb; count_rows integer := 0;
begin
  if p_key is null or p_key = '' or jsonb_typeof(p_rows) <> 'array' or jsonb_array_length(p_rows) = 0 or jsonb_array_length(p_rows) > 500 then
    raise exception 'invalid document';
  end if;
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_key, 0));
  update public.knowledge_documents set is_current=false, updated_by=p_actor, updated_at=now()
  where document_key=p_key and is_current and id not in (select x->>'id' from jsonb_array_elements(p_rows) x);
  for item in select * from jsonb_array_elements(p_rows) loop
    insert into public.knowledge_documents(id, lesson_id, kc_code, text, source, document_key, updated_by)
    values (item->>'id', item->>'lesson_id', item->>'kc_code', item->>'text', item->>'source', p_key, p_actor)
    on conflict (id) do nothing;
    update public.knowledge_documents set is_current=true, updated_by=p_actor, updated_at=now()
    where id=item->>'id' and document_key=p_key and not is_current;
    count_rows := count_rows + 1;
  end loop;
  return count_rows;
end $$;
revoke all on function public.ingest_knowledge_document(text,jsonb,uuid) from public, anon, authenticated;
grant execute on function public.ingest_knowledge_document(text,jsonb,uuid) to service_role;
