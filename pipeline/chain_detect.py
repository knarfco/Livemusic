"""Best-effort, automatic, non-blocking chain filtering.

Two signals, both automatic: a curated denylist of known corporate brand
names, and OpenStreetMap's own `brand` tag (set on most chain locations).
Neither is exhaustive on purpose -- a false negative here just means one
chain slips through and gets cleaned up later; a false positive would wrongly
drop a real independent business, which is worse. No human review step.
"""

from pathlib import Path

from normalize import normalize_name

DENYLIST_PATH = Path(__file__).parent / "chain_denylist.txt"


def load_denylist(path: Path = DENYLIST_PATH) -> list[str]:
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        norm = normalize_name(line)
        if norm:
            names.append(norm)
    return names


def is_chain(name: str, denylist: list[str], brand: str | None = None) -> bool:
    if brand and brand.strip():
        return True
    norm = normalize_name(name)
    if not norm:
        return False
    return any(entry in norm for entry in denylist)
