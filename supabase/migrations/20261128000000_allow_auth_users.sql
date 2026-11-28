-- Mọi tài khoản còn tồn tại trong Supabase Auth đều được truy cập.
create or replace function public.is_allowed_coach() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from auth.users where id = (select auth.uid()));
$$;
