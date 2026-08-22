-- Lets the free/unpaid directory show "something's happening tonight" for a
-- venue WITHOUT revealing the band name or time — that's the upgrade hook.
-- A view, not a table: it deliberately bypasses the shows RLS restriction
-- (which normally hides shows from inactive venues) to expose only the bare
-- fact "this venue has a show on this date," nothing else.

create view public_show_flags as
  select venue_id, show_date from shows;

grant select on public_show_flags to anon, authenticated;
