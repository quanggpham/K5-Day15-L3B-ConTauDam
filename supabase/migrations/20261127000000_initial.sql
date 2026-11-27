create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  role text not null default 'coach'
);
create table public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  lesson_id text not null,
  metrics_snapshot jsonb not null default '{}'::jsonb,
  status text not null default 'pending',
  model text,
  created_at timestamptz not null default now()
);
create table public.recommendations (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  kc_code text not null,
  priority integer not null check (priority > 0),
  content text not null,
  citations jsonb not null default '[]'::jsonb
);
create table public.evaluation_results (
  id uuid primary key default gen_random_uuid(),
  analysis_run_id uuid not null references public.analysis_runs(id) on delete cascade,
  metrics jsonb not null default '{}'::jsonb,
  judge text,
  passed boolean
);
create index analysis_runs_user_id_idx on public.analysis_runs(user_id);
create index recommendations_run_id_idx on public.recommendations(analysis_run_id);
create index evaluation_results_run_id_idx on public.evaluation_results(analysis_run_id);

create function public.handle_new_user() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name) values (new.id, new.raw_user_meta_data ->> 'display_name');
  return new;
end;
$$;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.recommendations enable row level security;
alter table public.evaluation_results enable row level security;
revoke all on public.profiles, public.analysis_runs, public.recommendations, public.evaluation_results from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;
grant select, insert, update, delete on public.analysis_runs, public.recommendations, public.evaluation_results to authenticated;
create policy profiles_select on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy profiles_update on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));
create policy runs_owner on public.analysis_runs for all to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy recommendations_owner on public.recommendations for all to authenticated using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid()))) with check (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
create policy evaluation_owner on public.evaluation_results for all to authenticated using (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid()))) with check (exists (select 1 from public.analysis_runs r where r.id = analysis_run_id and r.user_id = (select auth.uid())));
