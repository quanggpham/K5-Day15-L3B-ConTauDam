\set ON_ERROR_STOP 1
begin;
create function pg_temp.onehot(k int) returns text language sql as $$
  select '[' || string_agg(case when i = k then '1' else '0' end, ',' order by i) || ']' from generate_series(1, 384) i
$$;
select public.ingest_knowledge_document('test/kb', '[{"id":"test:a","lesson_id":"L1","kc_code":"K1","text":"alpha","source":"test/kb"},{"id":"test:b","lesson_id":"L1","kc_code":"K1","text":"beta","source":"test/kb"}]'::jsonb, null);
do $$
declare n integer;
begin
  n := public.set_knowledge_embeddings('test-model', jsonb_build_array(
    jsonb_build_object('id', 'test:a', 'embedding', pg_temp.onehot(1)),
    jsonb_build_object('id', 'test:b', 'embedding', pg_temp.onehot(2)),
    jsonb_build_object('id', 'test:missing', 'embedding', pg_temp.onehot(3))));
  if n <> 2 then raise exception 'expected 2 embedded rows, got %', n; end if;
  if exists (select 1 from public.knowledge_document_history where document_id like 'test:%') then
    raise exception 'loading embeddings must not create history';
  end if;
  if exists (select 1 from public.match_knowledge_documents(pg_temp.onehot(1)::extensions.vector, 'L1', 'K1', 3)) then
    raise exception 'unapproved documents must not match';
  end if;
  update public.knowledge_documents set approved = true where id like 'test:%';
  if (select array_agg(id order by similarity desc) from public.match_knowledge_documents(pg_temp.onehot(1)::extensions.vector, 'L1', 'K1', 3))
     is distinct from array['test:a', 'test:b'] then
    raise exception 'nearest document must come first';
  end if;
  update public.knowledge_documents set text = 'alpha v2' where id = 'test:a';
  if (select embedding is not null or embedding_model is not null from public.knowledge_documents where id = 'test:a') then
    raise exception 'editing text must clear the stale embedding';
  end if;
  begin
    perform public.set_knowledge_embeddings('test-model', '[{"id":"test:b","embedding":"[1,2,3]"}]'::jsonb);
    raise exception 'wrong dimensions accepted';
  exception when data_exception then null;
  end;
  if has_function_privilege('anon', 'public.match_knowledge_documents(extensions.vector,text,text,integer)', 'execute')
     or has_function_privilege('authenticated', 'public.set_knowledge_embeddings(text,jsonb)', 'execute') then
    raise exception 'KB vector functions must be service role only';
  end if;
end $$;
rollback;
