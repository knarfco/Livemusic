"""Quick hand-picked sanity checks, no network, no test framework needed.
Run with: python test_pipeline.py
"""

import chain_detect
import fetch_osm
import load
import normalize


def check(label, condition):
    status = "ok" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def main():
    results = []

    results.append(check(
        "normalize_name strips legal suffix",
        normalize.normalize_name("The Tiki Bar LLC") == "the tiki bar",
    ))
    results.append(check(
        "normalize_address expands abbreviation and drops suite",
        normalize.normalize_address("123 Main St Suite 4") == "123 main street",
    ))
    results.append(check(
        "dedup_key is stable for equivalent inputs",
        normalize.dedup_key("The Tiki Bar", "123 Main St", "32931")
        == normalize.dedup_key("The Tiki Bar LLC", "123 Main Street Suite 2", "32931-1234"),
    ))
    results.append(check(
        "dedup_key is None without a usable address or coordinates",
        normalize.dedup_key("The Tiki Bar", "", "32931") is None,
    ))
    results.append(check(
        "dedup_key falls back to coordinates when there's no street address",
        normalize.dedup_key("The Tiki Bar", "", "32931", lat=28.32001, lng=-80.61001)
        == "the tiki bar|geo:28.3200,-80.6100|32931",
    ))

    results.append(check(
        "a restaurant-tagged tavern is reclassified as a bar",
        fetch_osm.classify_category("restaurant", {"name": "Joe's Tavern & Grill"}) == "bar",
    ))
    results.append(check(
        "a plain restaurant stays a restaurant",
        fetch_osm.classify_category("restaurant", {"name": "Mario's Italian Kitchen"}) == "restaurant",
    ))
    results.append(check(
        "amenity=pub is always a bar regardless of name",
        fetch_osm.classify_category("pub", {"name": "Mario's Italian Kitchen"}) == "bar",
    ))

    denylist = chain_detect.load_denylist()
    results.append(check(
        "known chain is caught by the denylist",
        chain_detect.is_chain("McDonald's #4021", denylist) is True,
    ))
    results.append(check(
        "a real independent is not flagged",
        chain_detect.is_chain("Joe's Local Tavern", denylist) is False,
    ))
    results.append(check(
        "an OSM brand tag alone is enough to flag as a chain",
        chain_detect.is_chain("Anything", denylist, brand="Some Chain Co") is True,
    ))

    # Regression: the same real place mapped as two OSM elements (e.g. a
    # building outline and a point) must collapse to one row before it ever
    # reaches the database -- ON CONFLICT DO UPDATE can't target a row twice
    # in the same statement.
    dupes = [
        {"dedup_key": "a", "name": "Tiki Bar (way)"},
        {"dedup_key": "a", "name": "Tiki Bar (node)"},
        {"dedup_key": "b", "name": "Different Place"},
    ]
    results.append(check(
        "duplicate dedup_keys within a batch collapse to one row",
        len(load.dedupe_records(dupes)) == 2,
    ))

    if not all(results):
        raise SystemExit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
