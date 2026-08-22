-- migration_008 tried to seed demo venues but ran into two real bugs and
-- inserted nothing (the venues INSERT and the shows INSERT both failed
-- outright, so nothing landed — but migration_008 is already marked
-- "applied" by the tracker, so it will never run again). This migration
-- is the corrected version, as a new file so it actually runs.
--
-- Bug 1: three of the four demo venues use paid tiers (stage_left,
-- stage_right, center_stage), and the zip-exclusivity trigger added in
-- migration_007 requires a zip_code for those tiers — the original insert
-- didn't supply one, so the trigger rejected the whole statement.
-- Bug 2: the shows insert combined three SELECTs with UNION ALL, which
-- made Postgres unable to tell that the '20:00'-style literals should be
-- read as a time value, so it errored instead of guessing.

insert into venues (name, address, city, slug, is_active, tier, zip_code) values
  ('Coral Reef Tavern', '100 Coral Reef Dr', 'Cocoa Beach', 'coral-reef-tavern-demo', false, 'basic', '32931'),
  ('Sunset Sound Bar', '300 N Atlantic Ave', 'Cocoa Beach', 'sunset-sound-bar-demo', true, 'stage_left', '32931'),
  ('Salt Air Lounge', '400 Minutemen Cswy', 'Cocoa Beach', 'salt-air-lounge-demo', true, 'stage_right', '32931'),
  ('The Golden Wave', '500 Ocean Beach Blvd', 'Cocoa Beach', 'golden-wave-demo', true, 'center_stage', '32931')
on conflict (slug) do nothing;

insert into shows (venue_id, show_date, start_time, band_name)
select v.id, current_date, '20:00'::time, 'The Neon Tide'
from venues v
where v.slug = 'sunset-sound-bar-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date);

insert into shows (venue_id, show_date, start_time, band_name)
select v.id, current_date, '21:00'::time, 'Salt & Sway'
from venues v
where v.slug = 'salt-air-lounge-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date);

insert into shows (venue_id, show_date, start_time, band_name)
select v.id, current_date, '22:00'::time, 'The Wavelengths'
from venues v
where v.slug = 'golden-wave-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date);
