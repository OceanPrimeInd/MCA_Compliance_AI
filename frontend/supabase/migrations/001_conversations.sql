-- Run this in Supabase Dashboard → SQL Editor → New query

create table if not exists public.conversations (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'Untitled',
  messages jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

-- Speeds up "list my conversations, most recent first"
create index if not exists conversations_user_id_updated_at_idx
  on public.conversations (user_id, updated_at desc);

-- Row Level Security: each user can only ever see/edit their own rows.
-- Without this, the anon key would let any logged-in user read everyone's chats.
alter table public.conversations enable row level security;

create policy "Users can view own conversations"
  on public.conversations for select
  using (auth.uid() = user_id);

create policy "Users can insert own conversations"
  on public.conversations for insert
  with check (auth.uid() = user_id);

create policy "Users can update own conversations"
  on public.conversations for update
  using (auth.uid() = user_id);

create policy "Users can delete own conversations"
  on public.conversations for delete
  using (auth.uid() = user_id);
