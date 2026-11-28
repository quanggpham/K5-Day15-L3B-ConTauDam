\set ON_ERROR_STOP 1
begin;
insert into auth.users (id, email, raw_user_meta_data) values
 ('00000000-0000-0000-0000-00000000000a','a@test.local','{}'),
 ('00000000-0000-0000-0000-00000000000b','b@test.local','{}');
insert into public.analysis_runs (id,user_id,lesson_id) values ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000000a','L1');
insert into public.recommendations (id,analysis_run_id,kc_code,priority,content,jev_score) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000001','KC1',1,'goc','{"s":1}');

set local role service_role;
do $$
declare r jsonb; run uuid := '10000000-0000-0000-0000-000000000001'; rec uuid := '20000000-0000-0000-0000-000000000001';
a uuid := '00000000-0000-0000-0000-00000000000a'; b uuid := '00000000-0000-0000-0000-00000000000b';
begin
 r := public.review_recommendation(run,rec,1,'bogus',null,null,a,null); assert r->>'outcome'='invalid_input', 'T1 '||r;
 r := public.review_recommendation(run,rec,1,'accept',null,'x',a,null); assert r->>'outcome'='invalid_input', 'T2 '||r;
 r := public.review_recommendation(run,rec,1,'accept',null,null,b,null); assert r->>'outcome'='not_found', 'T3 other owner '||r;
 r := public.review_recommendation(run,rec,1,'edited',null,'x',a,null); assert r->>'outcome'='invalid_transition', 'T4 '||r;
 r := public.review_recommendation(run,rec,1,'accept','ok',null,a,'a@test.local'); assert r->>'outcome'='ok' and (r->'recommendation'->>'version')='2', 'T5 '||r;
 assert not (r->'review' ? 'actor_email'), 'T5b actor_email leaked';
 -- tab 2 gửi cùng version 1 với quyết định khác -> conflict
 r := public.review_recommendation(run,rec,1,'reject',null,null,a,null); assert r->>'outcome'='version_conflict', 'T6 '||r;
 -- retry y hệt -> replayed
 r := public.review_recommendation(run,rec,1,'accept','ok',null,a,'a@test.local'); assert r->>'outcome'='replayed', 'T7 '||r;
 r := public.review_recommendation(run,rec,2,'request_changes',null,null,a,null); assert r->>'outcome'='ok', 'T8 '||r;
 r := public.review_recommendation(run,rec,3,'accept',null,null,a,null); assert r->>'outcome'='invalid_transition', 'T9 '||r;
 r := public.review_recommendation(run,rec,3,'edited',null,'ban sua',a,null); assert r->>'outcome'='ok'
   and (r->'recommendation'->>'is_edited')='true' and (r->'recommendation'->>'needs_rereview')='true'
   and r->'recommendation'->'jev_score'='null'::jsonb, 'T10 '||r;
 -- replay cũ bị ghi đè -> conflict
 r := public.review_recommendation(run,rec,1,'accept','ok',null,a,'a@test.local'); assert r->>'outcome'='version_conflict', 'T11 '||r;
 assert (select count(*) from public.recommendation_reviews)=3, 'T12 audit count';
 begin delete from public.recommendation_reviews; raise exception 'T13 delete allowed';
 exception when others then assert sqlerrm like '%append-only%' or sqlerrm like '%permission%', 'T13 '||sqlerrm; end;
 begin update public.recommendation_reviews set comment='x'; raise exception 'T14 update allowed';
 exception when others then assert sqlerrm like '%append-only%', 'T14 '||sqlerrm; end;
 begin truncate public.recommendation_reviews; raise exception 'T15 truncate allowed';
 exception when insufficient_privilege then null; end;
end $$;
reset role;

-- quyền: authenticated không gọi được RPC, không ghi trực tiếp
set local role authenticated;
select set_config('request.jwt.claims','{"sub":"00000000-0000-0000-0000-00000000000a","email":"a@test.local","role":"authenticated"}',true);
do $$ begin
 assert public.is_allowed_coach(), 'T16a Auth user can access without allowlist';
 assert (select count(*) from public.recommendation_reviews)=3, 'T16 owner sees audit';
 begin perform public.review_recommendation(null,null,1,'accept',null,null,null,null); raise exception 'T17 rpc allowed';
 exception when insufficient_privilege then null; end;
 begin insert into public.recommendation_reviews(run_id,recommendation_id,expected_version,new_version,decision,actor_id)
   values ('10000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001',1,2,'accept','00000000-0000-0000-0000-00000000000a');
   raise exception 'T18 insert allowed';
 exception when insufficient_privilege then null; end;
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-0000-0000-00000000000b","email":"b@test.local","role":"authenticated"}',true);
do $$ begin
 assert public.is_allowed_coach(), 'T19a second Auth user can access';
 assert (select count(*) from public.recommendation_reviews)=0, 'T19 other owner sees audit';
end $$;
select set_config('request.jwt.claims','{"sub":"00000000-0000-0000-0000-00000000000c","role":"authenticated"}',true);
do $$ begin assert not public.is_allowed_coach(), 'T19b unknown user denied'; end $$;
reset role;

-- cascade: xoá run -> recs + audit biến mất
delete from public.analysis_runs where id='10000000-0000-0000-0000-000000000001';
do $$ begin assert (select count(*) from public.recommendation_reviews)=0 and (select count(*) from public.recommendations)=0, 'T20 cascade'; end $$;
-- cascade từ user
insert into public.analysis_runs (id,user_id,lesson_id) values ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-00000000000a','L1');
insert into public.recommendations (id,analysis_run_id,kc_code,priority,content) values ('20000000-0000-0000-0000-000000000002','10000000-0000-0000-0000-000000000002','KC1',1,'g');
select public.review_recommendation('10000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000002',1,'accept',null,null,'00000000-0000-0000-0000-00000000000a',null);
delete from auth.users where id='00000000-0000-0000-0000-00000000000a';
do $$ begin assert (select count(*) from public.recommendation_reviews)=0, 'T21 user cascade'; end $$;
select 'ALL PASS' as result;
rollback;
