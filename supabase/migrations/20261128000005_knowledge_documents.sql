-- Forward-only, expand step. Lesson KB cho RAG (BM25 + lọc lesson_id/kc_code), không embedding.
-- Chỉ backend (service role) đọc/ghi: bật RLS và KHÔNG tạo policy cho anon/authenticated.
-- Mọi document mặc định approved=false; người duyệt đổi sang true sau khi kiểm nguồn.
-- CHƯA chạy thử trên Postgres/Supabase thật: thử bằng `supabase db reset` ở staging trước khi lên production.
-- DOWN:
--   drop table public.knowledge_documents;

create table public.knowledge_documents (
  id text primary key,
  lesson_id text not null check (length(lesson_id) between 1 and 64),
  kc_code text not null check (length(kc_code) between 1 and 128),
  text text not null check (length(text) between 1 and 8000),
  source text not null check (length(source) between 1 and 256),
  approved boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index knowledge_documents_lookup_idx
  on public.knowledge_documents (lesson_id, kc_code) where approved;

alter table public.knowledge_documents enable row level security;
revoke all on public.knowledge_documents from anon, authenticated;
