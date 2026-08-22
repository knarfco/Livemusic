-- Makes zip-code exclusivity a real, enforced rule instead of a promise:
-- at most 1 Center Stage and 2 each of Stage Left / Stage Right per zip
-- code. Trying to assign a slot that's already full fails with a clear
-- error right in the Table Editor — it's not possible to oversell by accident.
-- "zip_code" is a plain text field on purpose, to support postal codes
-- from other countries later, not just 5-digit US zips.

alter table venues add column if not exists zip_code text;

create or replace function enforce_tier_zip_limits()
returns trigger as $$
declare
  cap integer;
  existing_count integer;
begin
  if new.tier = 'center_stage' then cap := 1;
  elsif new.tier in ('stage_left', 'stage_right') then cap := 2;
  else
    return new; -- basic/free tier, no limit
  end if;

  if new.zip_code is null then
    raise exception 'A zip/postal code is required before assigning % tier', new.tier;
  end if;

  select count(*) into existing_count
  from venues
  where zip_code = new.zip_code
    and tier = new.tier
    and id <> new.id;

  if existing_count >= cap then
    raise exception 'Zip code % already has the maximum number of % slots (%)', new.zip_code, new.tier, cap;
  end if;

  return new;
end;
$$ language plpgsql;

drop trigger if exists venues_tier_zip_limit on venues;
create trigger venues_tier_zip_limit
  before insert or update of tier, zip_code on venues
  for each row execute function enforce_tier_zip_limits();
