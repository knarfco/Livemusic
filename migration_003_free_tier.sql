-- Run this in Supabase SQL Editor after migration_002_self_signup.sql.
-- Splits the model into: free listing (name + address, always public) vs.
-- $8.97/mo paid "Stage" feature (publishing an actual live schedule).

alter table venues add column if not exists address text;

-- Every venue's basic listing (name, address, city) is public and free —
-- no payment required just to be listed. Only the SHOWS stay gated to
-- paid/active venues (see migration_002 — that policy is unchanged).
drop policy if exists "public can read venues" on venues;
drop policy if exists "public can read active venues" on venues;
create policy "public can read venues" on venues for select using (true);
