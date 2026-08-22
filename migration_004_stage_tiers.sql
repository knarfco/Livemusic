-- Run after migrations 002 and 003.
-- Adds featured-placement tiers: basic (default, $8.97 tier), stage_left /
-- stage_right (equal-weight featured spots), center_stage (top billing,
-- your call how many venues you actually sell this to — nothing in the
-- database limits it, that's a sales discipline, not a technical one).

alter table venues add column if not exists tier text not null default 'basic';
alter table venues add constraint venues_tier_check
  check (tier in ('basic', 'stage_left', 'stage_right', 'center_stage'));
