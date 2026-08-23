"""Quick hand-picked sanity checks, no network, no test framework needed.
Run with: python test_pipeline.py
"""

import chain_detect
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
        "dedup_key is None without a usable address",
        normalize.dedup_key("The Tiki Bar", "", "32931") is None,
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

    if not all(results):
        raise SystemExit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
