-- Chỉ quản trị viên database được quản lý danh sách email.
create table public.coach_allowlist (
  email text primary key check (email = lower(btrim(email)) and email <> ''),
  created_at timestamptz not null default now()
);
alter table public.coach_allowlist enable row level security;
revoke all on public.coach_allowlist from anon, authenticated;

create function public.is_allowed_coach() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.coach_allowlist where email = lower((select auth.jwt()) ->> 'email'));
$$;
revoke all on function public.is_allowed_coach() from public, anon;
grant execute on function public.is_allowed_coach() to authenticated;

create policy allowlist_profiles on public.profiles as restrictive for all to authenticated
  using ((select public.is_allowed_coach())) with check ((select public.is_allowed_coach()));
create policy allowlist_runs on public.analysis_runs as restrictive for all to authenticated
  using ((select public.is_allowed_coach())) with check ((select public.is_allowed_coach()));
create policy allowlist_recommendations on public.recommendations as restrictive for all to authenticated
  using ((select public.is_allowed_coach())) with check ((select public.is_allowed_coach()));
create policy allowlist_evaluation on public.evaluation_results as restrictive for all to authenticated
  using ((select public.is_allowed_coach())) with check ((select public.is_allowed_coach()));
