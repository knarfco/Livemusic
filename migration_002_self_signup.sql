-- Run this in Supabase SQL Editor (New query -> paste -> Run) on the EXISTING
-- database — this adds self-signup on top of what schema.sql already created.
-- Safe to run once; do not re-run schema.sql itself (tables already exist).

alter table venues add column is_active boolean not null default false;

-- A venue can now be created by the person signing up, not just by you.
create policy "owner can create own venue" on venues for insert
  with check (owner_user_id = auth.uid());

-- A venue owner can always see their own row, even before you've activated them
-- (so they can log in and see "pending" status).
create policy "owner can read own venue" on venues for select
  using (owner_user_id = auth.uid());

-- The public (the /index.html schedule page) can now only see ACTIVE venues
-- and their shows — nothing shows up publicly until you flip is_active to true.
drop policy "public can read venues" on venues;
create policy "public can read active venues" on venues for select
  using (is_active = true);

drop policy "public can read shows" on shows;
create policy "public can read active venue shows" on shows for select
  using (venue_id in (select id from venues where is_active = true));
