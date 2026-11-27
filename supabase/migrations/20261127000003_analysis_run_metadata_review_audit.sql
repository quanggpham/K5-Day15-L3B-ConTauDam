-- Forward-only. Expand step: thêm metadata cho analysis run, audit duyệt append-only, khóa ghi trực tiếp từ browser.
-- Không DROP/TRUNCATE/DELETE. Bản nháp cũ giữ nguyên: cột mới nullable hoặc có default; không bịa giá trị cho dữ liệu cũ.
-- Lưu ý khóa: bảng nhỏ nên CREATE INDEX thường (Supabase chạy migration trong transaction, không dùng được CONCURRENTLY).
-- Nếu bảng lớn, tạo các index này bằng CONCURRENTLY ngoài migration trước khi áp dụng.
-- Snapshot JSON dùng lại cột có sẵn analysis_runs.metrics_snapshot (không thêm cột trùng).

-- 1) analysis_runs: owner = user_id (backend gán từ auth.uid()/JWT, không nhận từ client).
-- DOWN: alter table public.analysis_runs drop column request_id, drop column snapshot_version, drop column ai_status,
--       drop column ai_status_reason, drop column version, drop column updated_at;  (xóa constraint/index kèm theo)
alter table public.analysis_runs
  add column request_id text,
  add column snapshot_version text,
  add column ai_status text,
  add column ai_status_reason text,
  add column version integer not null default 1,
  add column updated_at timestamptz not null default now();
-- Backfill updated_at cho nháp cũ (một UPDATE; nếu bảng lớn thì chia batch theo id).
update public.analysis_runs set updated_at = created_at where updated_at > created_at;
-- ai_status NULL ở nháp cũ = "chưa ghi nhận"; backend phải hiển thị rõ, không suy diễn.
alter table public.analysis_runs
  add constraint analysis_runs_ai_status_check check (ai_status is null or ai_status in ('not_enabled','blocked','ready','failed')),
  add constraint analysis_runs_version_check check (version >= 1),
  add constraint analysis_runs_request_id_check check (request_id is null or (btrim(request_id) <> '' and length(request_id) <= 128)),
  add constraint analysis_runs_lesson_id_check check (btrim(lesson_id) <> '') not valid;  -- not valid: không chặn nháp cũ

-- Idempotency: một request_id / owner. Cùng request_id + lesson_id khác => backend SELECT theo (user_id, request_id),
-- so lesson_id; khác thì trả 409. Insert race: bắt unique_violation rồi SELECT lại.
-- DOWN: drop index public.analysis_runs_owner_request_uidx;
create unique index analysis_runs_owner_request_uidx on public.analysis_runs (user_id, request_id) where request_id is not null;
-- List/phân trang keyset theo (created_at desc, id desc).
-- DOWN: drop index public.analysis_runs_owner_created_idx, public.analysis_runs_owner_lesson_created_idx, public.analysis_runs_owner_ai_created_idx;
create index analysis_runs_owner_created_idx on public.analysis_runs (user_id, created_at desc, id desc);
create index analysis_runs_owner_lesson_created_idx on public.analysis_runs (user_id, lesson_id, created_at desc, id desc);
create index analysis_runs_owner_ai_created_idx on public.analysis_runs (user_id, ai_status, created_at desc, id desc);

-- Trigger tự tăng updated_at (version do backend tăng khi review: update ... where version = expected).
-- DOWN: drop trigger analysis_runs_touch on public.analysis_runs; drop function public.touch_updated_at();
create function public.touch_updated_at() returns trigger language plpgsql set search_path = '' as $$
begin new.updated_at = now(); return new; end;
$$;
revoke execute on function public.touch_updated_at() from public, anon, authenticated;
create trigger analysis_runs_touch before update on public.analysis_runs for each row execute function public.touch_updated_at();

-- 2) recommendations: trạng thái duyệt + phiên bản (optimistic locking theo đề xuất).
-- DOWN: alter table public.recommendations drop column version, drop column review_status, drop column is_edited,
--       drop column needs_rereview, drop column jev_score, drop column updated_at;
alter table public.recommendations
  add column version integer not null default 1,
  add column review_status text,
  add column is_edited boolean not null default false,
  add column needs_rereview boolean not null default false,
  add column jev_score jsonb,
  add column updated_at timestamptz not null default now(),
  add constraint recommendations_version_check check (version >= 1),
  add constraint recommendations_review_status_check check (review_status is null or review_status in ('pending','accepted','rejected','changes_requested','edited')),
  -- Bản sửa tay: bắt buộc cờ duyệt lại, KHÔNG mang điểm JEV của bản gốc.
  add constraint recommendations_edited_no_jev_check check (not is_edited or (needs_rereview and jev_score is null));
create trigger recommendations_touch before update on public.recommendations for each row execute function public.touch_updated_at();
-- DOWN: drop trigger recommendations_touch on public.recommendations;

-- 3) Audit duyệt append-only.
-- DOWN: drop table public.recommendation_reviews; drop function public.reject_review_mutation();
create table public.recommendation_reviews (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.analysis_runs(id) on delete cascade,
  recommendation_id uuid not null references public.recommendations(id) on delete cascade,
  expected_version integer not null check (expected_version >= 1),
  new_version integer not null check (new_version > expected_version),
  decision text not null check (decision in ('accept','reject','request_changes','edited')),
  comment text,
  content_before text,
  content_after text,
  needs_rereview boolean not null default false,
  actor_id uuid not null,   -- user id từ session, không FK để audit không phụ thuộc vòng đời profile
  actor_email text,
  at timestamptz not null default now(),
  constraint recommendation_reviews_edit_check check (decision <> 'edited' or (needs_rereview and content_after is not null))
);
create index recommendation_reviews_run_at_idx on public.recommendation_reviews (run_id, at, id);
create index recommendation_reviews_rec_at_idx on public.recommendation_reviews (recommendation_id, at, id);

-- Chặn UPDATE; chặn DELETE trực tiếp (xóa cascade từ run/user, depth > 1, vẫn được phép). CHƯA chạy thử hành vi cascade.
create function public.reject_review_mutation() returns trigger language plpgsql set search_path = '' as $$
begin
  if tg_op = 'UPDATE' or pg_trigger_depth() = 1 then
    raise exception 'recommendation_reviews is append-only';
  end if;
  return old;
end;
$$;
revoke execute on function public.reject_review_mutation() from public, anon, authenticated;
create trigger recommendation_reviews_append_only before update or delete on public.recommendation_reviews
  for each row execute function public.reject_review_mutation();

-- 4) RLS + quyền: browser chỉ SELECT; mọi ghi qua backend (service_role, bypass RLS, kiểm owner ở code).
-- DOWN (khôi phục hành vi cũ): grant insert, update, delete on public.analysis_runs, public.recommendations, public.evaluation_results to authenticated;
--       rồi tạo lại các policy *_owner dạng "for all" như migration 000000 sau khi drop policy *_owner_select.
alter table public.recommendation_reviews enable row level security;
revoke all on public.recommendation_reviews from anon, authenticated;
revoke insert, update, delete, truncate, references, trigger on public.analysis_runs, public.recommendations, public.evaluation_results from anon, authenticated;
grant select on public.analysis_runs, public.recommendations, public.evaluation_results, public.recommendation_reviews to authenticated;
grant all on public.analysis_runs, public.recommendations, public.evaluation_results, public.recommendation_reviews to service_role;

drop policy runs_owner on public.analysis_runs;
drop policy recommendations_owner on public.recommendations;
drop policy evaluation_owner on public.evaluation_results;
create policy runs_owner_select on public.analysis_runs for select to authenticated using (user_id = (select auth.uid()));
create policy recommendations_owner_select on public.recommendations for select to authenticated
  using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
create policy evaluation_owner_select on public.evaluation_results for select to authenticated
  using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
create policy reviews_owner_select on public.recommendation_reviews for select to authenticated
  using (exists (select 1 from public.analysis_runs r where r.id = run_id and r.user_id = (select auth.uid())));
-- Giữ ràng buộc allowlist (restrictive) cho bảng mới. DOWN: drop policy allowlist_reviews on public.recommendation_reviews;
create policy allowlist_reviews on public.recommendation_reviews as restrictive for all to authenticated
  using ((select public.is_allowed_coach())) with check ((select public.is_allowed_coach()));
