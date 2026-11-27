-- Trigger functions are invoked by Postgres, not directly through the public API.
revoke execute on function public.handle_new_user() from public, anon, authenticated;
