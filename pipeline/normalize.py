"""Name/address normalization shared by every source the pipeline reads from.

The output of these functions is never shown to a user -- it only exists so
two records for the same real-world venue collapse to the same dedup_key.
"""

import re

LEGAL_SUFFIXES = (
    "llc", "l l c", "inc", "incorporated", "corp", "corporation", "co", "ltd",
    "lp", "llp", "pllc", "pc",
)

STREET_ABBREVIATIONS = {
    "st": "street", "ave": "avenue", "av": "avenue", "blvd": "boulevard",
    "dr": "drive", "rd": "road", "ln": "lane", "ct": "court", "pl": "place",
    "sq": "square", "hwy": "highway", "pkwy": "parkway", "cir": "circle",
    "ter": "terrace", "trl": "trail", "n": "north", "s": "south", "e": "east",
    "w": "west", "ne": "northeast", "nw": "northwest", "se": "southeast",
    "sw": "southwest",
}

UNIT_MARKERS = re.compile(r"\b(ste|suite|unit|apt|#)\b.*$", re.IGNORECASE)


def _strip_punctuation(text: str) -> str:
    return re.sub(r"[^\w\s]", " ", text)


def normalize_name(name: str) -> str:
    if not name:
        return ""
    text = _strip_punctuation(name.lower())
    words = [w for w in text.split() if w not in LEGAL_SUFFIXES]
    return " ".join(words).strip()


def normalize_address(address: str) -> str:
    if not address:
        return ""
    address = UNIT_MARKERS.sub("", address)
    text = _strip_punctuation(address.lower())
    words = [STREET_ABBREVIATIONS.get(w, w) for w in text.split()]
    return " ".join(words).strip()


def normalize_zip(zip_code: str) -> str:
    if not zip_code:
        return ""
    match = re.search(r"\d{5}", zip_code)
    return match.group(0) if match else ""


def dedup_key(name: str, address: str, zip_code: str) -> str | None:
    norm_name = normalize_name(name)
    norm_address = normalize_address(address)
    norm_zip = normalize_zip(zip_code)
    if not norm_name or not norm_address:
        return None
    return f"{norm_name}|{norm_address}|{norm_zip}"


def slugify(name: str) -> str:
    text = _strip_punctuation(name.lower())
    return re.sub(r"\s+", "-", text.strip())
