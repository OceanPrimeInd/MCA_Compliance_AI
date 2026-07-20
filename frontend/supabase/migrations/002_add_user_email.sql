-- Run this in Supabase Dashboard → SQL Editor → New query
-- (after 001_conversations.sql has already been run)

alter table public.conversations
  add column if not exists user_email text;

-- Backfill existing rows (if any) from auth.users, so older conversations
-- saved before this column existed also show an email.
update public.conversations c
set user_email = u.email
from auth.users u
where c.user_id = u.id
  and c.user_email is null;
