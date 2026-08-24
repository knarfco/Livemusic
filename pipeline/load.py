"""Upserts pipeline records into the live venues table.

Writes over the same SUPABASE_DB_URL secret the migration workflow already
uses (a direct Postgres connection, bypassing RLS) -- no new secret needed.
Every write targets dedup_key, so running this again is always safe: an
existing venue gets its address/coordinates refreshed, a new one gets
inserted, and owner_user_id/is_active/tier/slug are never touched once set.
"""

import hashlib
import os

import psycopg2
import psycopg2.extras

from normalize import slugify

INSERT_COLUMNS = [
    "name", "slug", "address", "city", "state", "county", "zip_code",
    "phone", "category", "lat", "lng", "source", "source_ids", "dedup_key",
]

UPSERT_SQL = f"""
insert into venues ({", ".join(INSERT_COLUMNS)})
values %s
on conflict (dedup_key) do update set
  address = excluded.address,
  city = excluded.city,
  state = excluded.state,
  county = excluded.county,
  zip_code = excluded.zip_code,
  phone = coalesce(excluded.phone, venues.phone),
  category = excluded.category,
  lat = excluded.lat,
  lng = excluded.lng,
  source_ids = venues.source_ids || excluded.source_ids
"""


def get_connection():
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"])


def make_slug(name: str, dedup_key: str) -> str:
    # Deterministic from dedup_key, so re-running the pipeline never mints a
    # second slug for a venue that's already there.
    suffix = hashlib.sha1(dedup_key.encode()).hexdigest()[:8]
    return f"{slugify(name)}-{suffix}"


def to_row(record: dict) -> tuple:
    return (
        record["name"],
        make_slug(record["name"], record["dedup_key"]),
        record.get("address"),
        record["city"],
        record.get("state"),
        record.get("county"),
        record.get("zip_code"),
        record.get("phone"),
        record.get("category"),
        record.get("lat"),
        record.get("lng"),
        record["source"],
        psycopg2.extras.Json({record["source"]: record["source_id"]}),
        record["dedup_key"],
    )


def dedupe_records(records: list[dict]) -> list[dict]:
    # A single INSERT ... ON CONFLICT DO UPDATE can't target the same row
    # twice -- and the same real-world place sometimes shows up as more than
    # one OSM element (e.g. a building outline and a separate point). Keep
    # one record per dedup_key before batching so that never happens.
    return list({r["dedup_key"]: r for r in records}.values())


def upsert_venues(conn, records: list[dict], batch_size: int = 500) -> int:
    if not records:
        return 0
    rows = [to_row(r) for r in dedupe_records(records)]
    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            psycopg2.extras.execute_values(cur, UPSERT_SQL, rows[i:i + batch_size])
            conn.commit()
    return len(rows)
