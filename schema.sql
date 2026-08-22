-- Run this once in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run.
-- Sets up the two tables this app needs and locks them down so a venue
-- can only ever edit its own schedule, never anyone else's.

create table venues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  address text,
  city text not null default 'Cocoa Beach',
  owner_user_id uuid references auth.users(id),
  is_active boolean not null default false, -- true once they're paying for the Stage feature
  tier text not null default 'basic' check (tier in ('basic', 'stage_left', 'stage_right', 'center_stage')),
  lat double precision, lng double precision,
  created_at timestamptz not null default now()
);

create table shows (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid not null references venues(id) on delete cascade,
  show_date date not null,
  start_time time,
  band_name text not null,
  notes text,
  updated_at timestamptz not null default now()
);

create index shows_date_idx on shows(show_date);
create index shows_venue_idx on shows(venue_id);

alter table venues enable row level security;
alter table shows enable row level security;

-- Every venue's basic listing (name/address/city) is public and free —
-- being listed costs nothing. Only the actual SHOW SCHEDULE is gated to
-- venues paying for the Stage feature (is_active = true).
create policy "public can read venues" on venues for select using (true);
create policy "public can read active venue shows" on shows for select
  using (venue_id in (select id from venues where is_active = true));

-- A signed-up user can create their own venue row (self-signup) and can
-- always read their own row, even before you've activated them.
create policy "owner can create own venue" on venues for insert
  with check (owner_user_id = auth.uid());
create policy "owner can read own venue" on venues for select
  using (owner_user_id = auth.uid());

-- A venue's logged-in user can only change ITS OWN row, and only shows
-- that belong to a venue it owns.
create policy "venue can update own row" on venues for update
  using (owner_user_id = auth.uid());

create policy "venue can manage own shows" on shows for all
  using (venue_id in (select id from venues where owner_user_id = auth.uid()))
  with check (venue_id in (select id from venues where owner_user_id = auth.uid()));
