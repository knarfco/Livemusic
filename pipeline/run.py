"""Phase 1 orchestrator: OpenStreetMap, nationwide, one state at a time.

Normal operation is unattended -- run this with no arguments and it fetches
every state, filters out anything that looks like a corporate chain, and
upserts the rest into Supabase. If a source comes back broken (every state
fails, or nothing usable came back at all) this exits non-zero so the
GitHub Actions run itself shows red -- that's the whole safety net, nobody
has to watch it run.

--dry-run skips the database write and just prints the counts -- useful if
you ever want to sanity-check a change before it touches real data, but
never required.
"""

import argparse
import sys

import chain_detect
import fetch_osm
import load


def run(states: list[str], dry_run: bool) -> None:
    denylist = chain_detect.load_denylist()
    conn = None if dry_run else load.get_connection()

    total_fetched = 0
    total_excluded = 0
    total_written = 0
    failed_states = []

    for state_abbr, records in fetch_osm.fetch_all(states):
        try:
            kept = [
                r for r in records
                if not chain_detect.is_chain(r["name"], denylist, r.get("brand"))
            ]
        except Exception as exc:  # a genuinely broken state shouldn't kill the run
            print(f"[{state_abbr}] FAILED: {exc}", file=sys.stderr)
            failed_states.append(state_abbr)
            continue

        excluded = len(records) - len(kept)
        total_fetched += len(records)
        total_excluded += excluded

        if not dry_run and kept:
            written = load.upsert_venues(conn, kept)
            total_written += written

        print(f"[{state_abbr}] fetched={len(records)} chain_excluded={excluded}")

    if conn is not None:
        conn.close()

    print("---")
    print(f"total fetched: {total_fetched}")
    print(f"total chain-excluded: {total_excluded}")
    print(f"total kept: {total_fetched - total_excluded}")
    if not dry_run:
        print(f"total written (inserted/updated): {total_written}")
    if failed_states:
        print(f"states that failed to fetch: {', '.join(failed_states)}")

    if total_fetched == 0:
        raise SystemExit("Nothing came back from any state -- treating this as a broken run.")
    if len(failed_states) > len(states) // 2:
        raise SystemExit("More than half of all states failed to fetch -- treating this as a broken run.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--states", default=None,
        help="Comma-separated state abbreviations (default: all 50 + DC)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    states = args.states.split(",") if args.states else fetch_osm.STATE_ABBREVIATIONS
    run(states, args.dry_run)
