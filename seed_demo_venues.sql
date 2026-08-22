-- Demo/showcase data — NOT real venues. Run in Supabase SQL Editor after all
-- prior migrations. Creates one example venue per tier so you can see the
-- whole hierarchy live on the public page without setting up real logins.
-- These have no owner_user_id (nobody can log into them), and are safe to
-- delete later: delete from shows where venue_id in (select id from venues
-- where slug like '%-demo'); delete from venues where slug like '%-demo';

insert into venues (name, address, city, slug, is_active, tier) values
  ('Coral Reef Tavern', '100 Coral Reef Dr', 'Cocoa Beach', 'coral-reef-tavern-demo', false, 'basic'),
  ('Sunset Sound Bar', '300 N Atlantic Ave', 'Cocoa Beach', 'sunset-sound-bar-demo', true, 'stage_left'),
  ('Salt Air Lounge', '400 Minutemen Cswy', 'Cocoa Beach', 'salt-air-lounge-demo', true, 'stage_right'),
  ('The Golden Wave', '500 Ocean Beach Blvd', 'Cocoa Beach', 'golden-wave-demo', true, 'center_stage');

insert into shows (venue_id, show_date, start_time, band_name)
select id, current_date, '20:00', 'The Neon Tide' from venues where slug = 'sunset-sound-bar-demo'
union all
select id, current_date, '21:00', 'Salt & Sway' from venues where slug = 'salt-air-lounge-demo'
union all
select id, current_date, '22:00', 'The Wavelengths' from venues where slug = 'golden-wave-demo';
