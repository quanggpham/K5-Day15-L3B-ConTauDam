\set ON_ERROR_STOP 1
begin;
insert into auth.users(id, email, raw_user_meta_data) values ('00000000-0000-0000-0000-00000000000a', 'kb@test.local', '{}');
insert into public.knowledge_documents(id, lesson_id, kc_code, text, source, updated_by)
values ('test:1', 'L1', 'K1', 'Nội dung', 'Nguồn được phép', '00000000-0000-0000-0000-00000000000a');
update public.knowledge_documents set approved=true, reviewed_by='00000000-0000-0000-0000-00000000000a', reviewed_at=now(), updated_by='00000000-0000-0000-0000-00000000000a' where id='test:1';
do $$ begin
 assert (select approved and version=2 and reviewed_by is not null from public.knowledge_documents where id='test:1'), 'approval';
 assert (select count(*)=1 from public.knowledge_document_history where document_id='test:1'), 'approval history';
end $$;
update public.knowledge_documents set text='Nội dung sửa' where id='test:1';
do $$ begin
 assert (select not approved and version=3 and reviewed_by is null and reviewed_at is null from public.knowledge_documents where id='test:1'), 'edit resets approval';
 assert (select count(*)=2 from public.knowledge_document_history where document_id='test:1'), 'edit history';
end $$;
select public.ingest_knowledge_document('doc1', '[{"id":"a", "lesson_id":"L1", "kc_code":"K1", "text":"Bản cũ", "source":"Nguồn"}]'::jsonb, '00000000-0000-0000-0000-00000000000a');
update public.knowledge_documents set approved=true, reviewed_by='00000000-0000-0000-0000-00000000000a', reviewed_at=now() where id='a';
select public.ingest_knowledge_document('doc1', '[{"id":"b", "lesson_id":"L1", "kc_code":"K1", "text":"Bản mới", "source":"Nguồn"}]'::jsonb, '00000000-0000-0000-0000-00000000000a');
do $$ begin
 assert (select not approved and not is_current from public.knowledge_documents where id='a'), 'old revision retired';
 assert (select not approved and is_current from public.knowledge_documents where id='b'), 'new revision pending';
end $$;
set local role authenticated;
do $$ begin
 begin perform public.ingest_knowledge_document('x', '[]'::jsonb, null); raise exception 'authenticated can ingest'; exception when insufficient_privilege then null; end;
 begin perform 1 from public.knowledge_documents; raise exception 'authenticated can read KB directly'; exception when insufficient_privilege then null; end;
 begin perform 1 from public.knowledge_document_history; raise exception 'authenticated can read KB history directly'; exception when insufficient_privilege then null; end;
end $$;
rollback;
