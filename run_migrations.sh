#!/usr/bin/env bash
# Applies any migration_*.sql file that hasn't been run yet, in filename
# order, and remembers what's already been applied so it's always safe to
# re-run — nothing gets run twice.
set -euo pipefail

psql "$DATABASE_URL" -c "create table if not exists _migrations_applied (filename text primary key, applied_at timestamptz default now());"

for f in $(ls migration_*.sql 2>/dev/null | sort); do
  already=$(psql "$DATABASE_URL" -tAc "select 1 from _migrations_applied where filename = '$f';")
  if [ "$already" = "1" ]; then
    echo "Skipping $f (already applied)"
  else
    echo "Applying $f"
    psql "$DATABASE_URL" -f "$f"
    psql "$DATABASE_URL" -c "insert into _migrations_applied (filename) values ('$f');"
  fi
done
