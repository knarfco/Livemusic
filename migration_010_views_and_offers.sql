-- Two features for any PAID venue (is_active = true): a simple visit
-- counter ("how many times has a potential customer looked you up") and
-- a special-offer coupon venues can write themselves, with a claim count
-- so they can see whether it's actually getting used. Free listings don't
-- get either -- this is part of what upgrading unlocks.

create table if not exists venue_views (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid not null references venues(id) on delete cascade,
  viewed_at timestamptz not null default now()
);
create index if not exists venue_views_venue_idx on venue_views(venue_id);

create table if not exists venue_offers (
  venue_id uuid primary key references venues(id) on delete cascade,
  offer_text text not null,
  updated_at timestamptz not null default now()
);

create table if not exists offer_claims (
  id uuid primary key default gen_random_uuid(),
  venue_id uuid not null references venues(id) on delete cascade,
  claimed_at timestamptz not null default now()
);
create index if not exists offer_claims_venue_idx on offer_claims(venue_id);

alter table venue_views enable row level security;
alter table venue_offers enable row level security;
alter table offer_claims enable row level security;

-- Anyone browsing the public page can log a view or a claim -- that's the
-- whole point, it's counting real visitors. But only the venue's own owner
-- can ever read those numbers back.
drop policy if exists "anyone can log a view" on venue_views;
create policy "anyone can log a view" on venue_views for insert with check (true);

drop policy if exists "owner can read own views" on venue_views;
create policy "owner can read own views" on venue_views for select
  using (venue_id in (select id from venues where owner_user_id = auth.uid()));

-- Offer text is only visible to the public for venues that are currently
-- paid/active -- a free listing has no offer to show.
drop policy if exists "public can read active offers" on venue_offers;
create policy "public can read active offers" on venue_offers for select
  using (venue_id in (select id from venues where is_active = true));

drop policy if exists "owner can manage own offer" on venue_offers;
create policy "owner can manage own offer" on venue_offers for all
  using (venue_id in (select id from venues where owner_user_id = auth.uid()))
  with check (venue_id in (select id from venues where owner_user_id = auth.uid() and is_active = true));

drop policy if exists "anyone can log a claim" on offer_claims;
create policy "anyone can log a claim" on offer_claims for insert with check (true);

drop policy if exists "owner can read own claims" on offer_claims;
create policy "owner can read own claims" on offer_claims for select
  using (venue_id in (select id from venues where owner_user_id = auth.uid()));
