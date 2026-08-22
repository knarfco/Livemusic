-- Demo/showcase data — NOT real venues. Creates one example venue per tier
-- so the public page has something to show before real venues sign up.
-- These have no owner_user_id (nobody can log into them). Idempotent: safe
-- to apply more than once, and runs automatically as part of the normal
-- migration pipeline — no manual SQL needed.
-- To remove later: delete from shows where venue_id in (select id from
-- venues where slug like '%-demo'); delete from venues where slug like '%-demo';

insert into venues (name, address, city, slug, is_active, tier) values
  ('Coral Reef Tavern', '100 Coral Reef Dr', 'Cocoa Beach', 'coral-reef-tavern-demo', false, 'basic'),
  ('Sunset Sound Bar', '300 N Atlantic Ave', 'Cocoa Beach', 'sunset-sound-bar-demo', true, 'stage_left'),
  ('Salt Air Lounge', '400 Minutemen Cswy', 'Cocoa Beach', 'salt-air-lounge-demo', true, 'stage_right'),
  ('The Golden Wave', '500 Ocean Beach Blvd', 'Cocoa Beach', 'golden-wave-demo', true, 'center_stage')
on conflict (slug) do nothing;

insert into shows (venue_id, show_date, start_time, band_name)
select v.id, current_date, '20:00', 'The Neon Tide'
from venues v
where v.slug = 'sunset-sound-bar-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date)
union all
select v.id, current_date, '21:00', 'Salt & Sway'
from venues v
where v.slug = 'salt-air-lounge-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date)
union all
select v.id, current_date, '22:00', 'The Wavelengths'
from venues v
where v.slug = 'golden-wave-demo'
  and not exists (select 1 from shows s where s.venue_id = v.id and s.show_date = current_date);
