-- Run this once in Supabase: Dashboard -> SQL Editor -> New query -> paste -> Run.
-- Sets up the two tables this app needs and locks them down so a venue
-- can only ever edit its own schedule, never anyone else's.

create table venues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  city text not null default 'Cocoa Beach',
  owner_user_id uuid references auth.users(id),
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

-- Anyone (including the public site, with no login) can read venues and shows.
create policy "public can read venues" on venues for select using (true);
create policy "public can read shows" on shows for select using (true);

-- A venue's logged-in user can only change ITS OWN row, and only shows
-- that belong to a venue it owns.
create policy "venue can update own row" on venues for update
  using (owner_user_id = auth.uid());

create policy "venue can manage own shows" on shows for all
  using (venue_id in (select id from venues where owner_user_id = auth.uid()))
  with check (venue_id in (select id from venues where owner_user_id = auth.uid()));
