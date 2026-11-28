-- Rollback 3 migration áp lên production ngày 2026-11-28:
--   20261128000007_kb_embedding, 20261127000004_review_recommendation_rpc, 20261127000003_analysis_run_metadata_review_audit.
-- Theo thứ tự ngược, gom từ các dòng DOWN trong từng migration. Một transaction; lỗi thì không đổi gì.
--
-- MẤT DỮ LIỆU: xoá vector KB, metadata báo cáo (request_id, ai_status, version...), trạng thái duyệt và toàn bộ
-- bảng audit recommendation_reviews. Chụp lại trước khi chạy:
--   supabase db dump --remote=<ref> --data-only -f backup-before-rollback.sql
-- Code backend hiện tại cần các cột của 000003/000004: rollback DB thì phải deploy lại bản code trước đó.
-- Đã thử trên Postgres 17 + pgvector local: schema sau rollback khớp schema chưa áp 3 migration này.
-- Chạy: supabase db query --remote=<ref> -f supabase/rollback/20261128_rollback_000003_000004_000007.sql
\set ON_ERROR_STOP 1
begin;

-- 000007 kb_embedding
drop function public.set_knowledge_embeddings(text, jsonb);
drop function public.match_knowledge_documents(extensions.vector, text, text, integer);
drop trigger knowledge_document_embedding_reset on public.knowledge_documents;
drop function public.knowledge_document_embedding_reset();
drop index public.knowledge_documents_embedding_idx;
alter table public.knowledge_documents drop constraint knowledge_documents_embedding_pair_check,
  drop column embedding_model, drop column embedding;
drop extension vector;  -- production chưa bật vector trước 000007 (kiểm 2026-11-28)

-- 000004 review_recommendation_rpc
drop function public.review_recommendation(uuid, uuid, integer, text, text, text, uuid, text);
alter table public.recommendation_reviews drop constraint recommendation_reviews_status_before_check,
  drop constraint recommendation_reviews_status_after_check, drop column status_before, drop column status_after;

-- 000003 analysis_run_metadata_review_audit (khôi phục quyền ghi và policy "for all" của 000000)
drop policy allowlist_reviews on public.recommendation_reviews;
drop policy runs_owner_select on public.analysis_runs;
drop policy recommendations_owner_select on public.recommendations;
drop policy evaluation_owner_select on public.evaluation_results;
grant insert, update, delete on public.analysis_runs, public.recommendations, public.evaluation_results to authenticated;
create policy runs_owner on public.analysis_runs for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy recommendations_owner on public.recommendations for all to authenticated
  using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())))
  with check (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
create policy evaluation_owner on public.evaluation_results for all to authenticated
  using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())))
  with check (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
drop table public.recommendation_reviews;
drop function public.reject_review_mutation();
drop trigger recommendations_touch on public.recommendations;
alter table public.recommendations drop column version, drop column review_status, drop column is_edited,
  drop column needs_rereview, drop column jev_score, drop column updated_at;
drop trigger analysis_runs_touch on public.analysis_runs;
drop function public.touch_updated_at();
drop index public.analysis_runs_owner_request_uidx, public.analysis_runs_owner_created_idx,
  public.analysis_runs_owner_lesson_created_idx, public.analysis_runs_owner_ai_created_idx;
alter table public.analysis_runs drop constraint analysis_runs_lesson_id_check,
  drop column request_id, drop column snapshot_version, drop column ai_status,
  drop column ai_status_reason, drop column version, drop column updated_at;

-- Lịch sử migration (chỉ có trên Supabase) để `db push` áp lại được sau khi sửa.
do $$ begin
  if to_regclass('supabase_migrations.schema_migrations') is not null then
    delete from supabase_migrations.schema_migrations
    where version in ('20261127000003', '20261127000004', '20261128000007');
  end if;
end $$;

commit;
