-- Adds what the automated nationwide venue-import pipeline needs: real
-- state/county/category/phone fields (every row so far has implicitly meant
-- one town), source tracking so we know where a row came from, and a
-- dedup_key so the pipeline can safely re-run forever without ever creating
-- duplicate rows for the same real-world business.

alter table venues add column if not exists state text;
alter table venues add column if not exists county text;
alter table venues add column if not exists category text
  check (category in ('bar', 'restaurant', 'food_and_drink'));
alter table venues add column if not exists phone text;

-- Where this row came from ('osm', 'fl_abt', 'self_signup', 'manual', ...) and
-- the id(s) it's known by in each source it's been matched against, e.g.
-- {"osm": "node/123456789", "fl_abt": "BEV1234567"}.
alter table venues add column if not exists source text;
alter table venues add column if not exists source_ids jsonb not null default '{}'::jsonb;

-- normalize(name) || '|' || normalize(street_address) || '|' || zip5, computed
-- by the pipeline. The unique index is what makes every import run an upsert
-- instead of a fresh insert -- running the pipeline again never duplicates a
-- venue that's already there.
alter table venues add column if not exists dedup_key text;
create unique index if not exists venues_dedup_key_idx on venues (dedup_key);

-- Lets a signed-up owner claim a venue the pipeline already listed for free,
-- instead of always creating a second duplicate row (see signup.html). Only
-- covers rows nobody owns yet -- once owner_user_id is set, "venue can update
-- own row" (schema.sql) is the policy that applies, not this one.
create policy "user can claim unclaimed venue" on venues for update
  using (owner_user_id is null)
  with check (owner_user_id = auth.uid());
