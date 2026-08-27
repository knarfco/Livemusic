"""Phase 1 orchestrator: multiple free sources, nationwide, one state at a time.

Normal operation is unattended -- run this with no arguments and it fetches
every state from every source below, filters out anything that looks like a
corporate chain, and upserts the rest into Supabase. Each source is fully
independent: if one comes back broken (every state fails, or nothing usable
came back at all), the run still finishes using whatever other sources are
healthy. Only if every source is broken does this exit non-zero so the
GitHub Actions run itself shows red -- that's the whole safety net, nobody
has to watch it run.

Adding a third/fourth source later is just adding its fetch module to
SOURCES below -- everything else (chain filtering, dedup, upsert, per-source
failure isolation) already generalizes.

--dry-run skips the database write and just prints the counts -- useful if
you ever want to sanity-check a change before it touches real data, but
never required.
"""

import argparse
import sys
import time

import chain_detect
import fetch_osm
import fetch_overture
import load

SOURCES = (fetch_osm, fetch_overture)


def run_source(source, state_abbr: str, denylist, conn, dry_run: bool) -> tuple[int, int, int]:
    records = source.fetch_state(state_abbr)
    kept = [
        r for r in records
        if not chain_detect.is_chain(r["name"], denylist, r.get("brand"))
    ]
    excluded = len(records) - len(kept)
    written = 0
    if not dry_run and kept:
        written = load.upsert_venues(conn, kept)
    return len(records), excluded, written


def run(states: list[str], dry_run: bool) -> None:
    denylist = chain_detect.load_denylist()
    conn = None if dry_run else load.get_connection()

    stats = {
        source.SOURCE_NAME: {"fetched": 0, "excluded": 0, "written": 0, "failed": []}
        for source in SOURCES
    }

    for i, state_abbr in enumerate(states):
        for source in SOURCES:
            source_stats = stats[source.SOURCE_NAME]
            try:
                fetched, excluded, written = run_source(source, state_abbr, denylist, conn, dry_run)
                source_stats["fetched"] += fetched
                source_stats["excluded"] += excluded
                source_stats["written"] += written
                print(f"[{state_abbr}] {source.SOURCE_NAME}: fetched={fetched} chain_excluded={excluded} written={written}")
            except Exception as exc:  # a genuinely broken state/source shouldn't kill the run
                print(f"[{state_abbr}] {source.SOURCE_NAME} FAILED: {exc}", file=sys.stderr)
                source_stats["failed"].append(state_abbr)
                if conn is not None:
                    conn.rollback()  # clear the failed transaction so the next fetch can still write

        if i < len(states) - 1:
            time.sleep(fetch_osm.DELAY_BETWEEN_STATES_SECONDS)

    if conn is not None:
        conn.close()

    print("---")
    any_source_alive = False
    for source in SOURCES:
        s = stats[source.SOURCE_NAME]
        kept = s["fetched"] - s["excluded"]
        line = f"{source.SOURCE_NAME}: fetched={s['fetched']} chain_excluded={s['excluded']} kept={kept}"
        if not dry_run:
            line += f" written={s['written']}"
        print(line)
        if s["failed"]:
            print(f"  states that failed: {', '.join(s['failed'])}")
        if s["fetched"] > 0 and len(s["failed"]) <= len(states) // 2:
            any_source_alive = True

    if not any_source_alive:
        raise SystemExit("Every source came back broken -- treating this as a broken run.")


if __name__ == "__main__":
    source_names = [s.SOURCE_NAME for s in SOURCES]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--states", default=None,
        help="Comma-separated state abbreviations (default: all 50 + DC)",
    )
    parser.add_argument(
        "--source", default=None, choices=source_names,
        # Each source runs as its own parallel GitHub Actions job (see
        # import_venues.yml) so two slow downloads-per-state don't add up
        # into one job long enough to hit the 6-hour hosted-runner cap.
        # Defaults to every source for local/manual use.
        help="Only run this one source (default: all sources)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.source:
        SOURCES = tuple(s for s in SOURCES if s.SOURCE_NAME == args.source)

    states = args.states.split(",") if args.states else fetch_osm.STATE_ABBREVIATIONS
    run(states, args.dry_run)
