-- Lets any paid venue (is_active = true) publish a short "today's specials"
-- blurb -- happy hour, a daily deal, a one-off event -- the same self-serve
-- way bands publish their live schedule. Mainly for bars/restaurants that
-- don't have live music at all and otherwise have no reason to show up in
-- the paid tier, but any paid venue can use it. Reuses is_active as the
-- paid gate, same pattern as venue_offers.

create table if not exists venue_specials (
  venue_id uuid primary key references venues(id) on delete cascade,
  specials_text text not null,
  updated_at timestamptz not null default now()
);

alter table venue_specials enable row level security;

drop policy if exists "public can read active specials" on venue_specials;
create policy "public can read active specials" on venue_specials for select
  using (venue_id in (select id from venues where is_active = true));

drop policy if exists "owner can manage own specials" on venue_specials;
create policy "owner can manage own specials" on venue_specials for all
  using (venue_id in (select id from venues where owner_user_id = auth.uid()))
  with check (venue_id in (select id from venues where owner_user_id = auth.uid() and is_active = true));
