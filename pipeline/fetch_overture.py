"""Phase 1b nationwide source: Overture Maps' free, open Places dataset.

Complements OpenStreetMap. Overture blends in place data from Meta,
Microsoft, TomTom, and community sources on top of OSM itself, so it tends
to catch small independent places OSM's mostly volunteer-mapped, stricter
tagging conventions miss entirely -- a place with a Facebook Business Page
but no formal street address, for example.

Downloaded one (deliberately generous, overlapping-at-the-edges) state
bounding box at a time via Overture's own `overturemaps` CLI, which streams
only the requested area from Overture's cloud-hosted GeoParquet -- never
the whole country. Any venue that shows up in both this and OpenStreetMap
collapses to a single row at load time (same dedup_key), so overlap between
adjacent state boxes -- or between this source and OSM -- is harmless.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

from normalize import dedup_key, normalize_zip

SOURCE_NAME = "overture"
DELAY_BETWEEN_STATES_SECONDS = 3
DOWNLOAD_TIMEOUT_SECONDS = 300
MAX_RETRIES = 2

# Below this, Overture itself is telling us the record is questionable --
# skip it rather than publish a possibly-nonexistent venue.
MIN_CONFIDENCE = 0.6

# Overture's Places taxonomy has ~2,300 categories; these are the ones that
# read as a bar-type vs. a restaurant-type place. Anything not in either set
# is skipped -- this pipeline isn't building a general business directory.
BAR_CATEGORIES = {
    "bar", "pub", "dive_bar", "sports_bar", "wine_bar", "cocktail_bar",
    "beer_bar", "brewery", "breweries", "beer_garden", "taproom",
    "gastropub", "night_club", "lounge", "bar_and_grill",
}
RESTAURANT_CATEGORIES = {
    "restaurant", "american_restaurant", "italian_restaurant",
    "mexican_restaurant", "seafood_restaurant", "diner", "cafe",
    "coffee_shop", "fast_food_restaurant",
}

# Deliberately generous (padded) bounding boxes -- west, south, east, north
# -- for the 50 states + DC. Precision doesn't matter here: a little
# cross-border overlap just means a venue gets fetched twice and collapses
# to one row via dedup_key; slight under-coverage at a true edge case is an
# acceptable gap for a free, best-effort, nationwide pass. Alaska/Hawaii use
# a box around their main landmass only (outlying islands excluded).
STATE_BBOXES = {
    "AL": (-88.6, 30.1, -84.8, 35.1), "AK": (-170.0, 51.1, -129.8, 71.6),
    "AZ": (-115.0, 31.2, -108.9, 37.1), "AR": (-94.7, 32.9, -89.5, 36.6),
    "CA": (-124.6, 32.4, -114.0, 42.1), "CO": (-109.2, 36.9, -101.9, 41.1),
    "CT": (-73.8, 40.9, -71.7, 42.1), "DE": (-75.9, 38.4, -75.0, 39.9),
    "FL": (-87.7, 24.4, -79.8, 31.1), "GA": (-85.7, 30.3, -80.7, 35.1),
    "HI": (-160.4, 18.8, -154.7, 22.3), "ID": (-117.3, 41.9, -111.0, 49.1),
    "IL": (-91.6, 36.9, -87.0, 42.6), "IN": (-88.2, 37.7, -84.7, 41.8),
    "IA": (-96.7, 40.3, -90.1, 43.6), "KS": (-102.1, 36.9, -94.5, 40.1),
    "KY": (-89.6, 36.4, -81.9, 39.2), "LA": (-94.1, 28.8, -88.7, 33.1),
    "ME": (-71.2, 42.9, -66.8, 47.5), "MD": (-79.5, 37.8, -75.0, 39.8),
    "MA": (-73.6, 41.2, -69.8, 42.9), "MI": (-90.5, 41.6, -82.1, 48.3),
    "MN": (-97.3, 43.4, -89.4, 49.4), "MS": (-91.7, 30.1, -88.0, 35.0),
    "MO": (-95.9, 35.9, -89.0, 40.7), "MT": (-116.1, 44.3, -104.0, 49.1),
    "NE": (-104.1, 39.9, -95.3, 43.1), "NV": (-120.1, 34.9, -113.9, 42.1),
    "NH": (-72.6, 42.6, -70.6, 45.4), "NJ": (-75.6, 38.8, -73.8, 41.4),
    "NM": (-109.1, 31.2, -102.9, 37.1), "NY": (-79.9, 40.4, -71.7, 45.1),
    "NC": (-84.4, 33.7, -75.3, 36.7), "ND": (-104.1, 45.9, -96.5, 49.1),
    "OH": (-84.9, 38.3, -80.4, 42.1), "OK": (-103.1, 33.5, -94.3, 37.1),
    "OR": (-124.7, 41.9, -116.4, 46.4), "PA": (-80.6, 39.6, -74.6, 42.6),
    "RI": (-71.9, 41.1, -71.0, 42.1), "SC": (-83.4, 32.0, -78.4, 35.3),
    "SD": (-104.1, 42.4, -96.4, 46.1), "TN": (-90.4, 34.9, -81.6, 36.8),
    "TX": (-106.7, 25.7, -93.4, 36.6), "UT": (-114.1, 36.9, -109.0, 42.1),
    "VT": (-73.5, 42.7, -71.4, 45.1), "VA": (-83.7, 36.5, -75.1, 39.5),
    "WA": (-124.9, 45.5, -116.9, 49.1), "WV": (-82.7, 37.1, -77.7, 40.7),
    "WI": (-92.9, 42.4, -86.2, 47.1), "WY": (-111.1, 40.9, -104.0, 45.1),
    "DC": (-77.15, 38.78, -76.9, 39.0),
}


def classify_category(categories: dict | None) -> str | None:
    categories = categories or {}
    candidates = [categories.get("primary")] + list(categories.get("alternate") or [])
    for candidate in candidates:
        if candidate in BAR_CATEGORIES:
            return "bar"
    for candidate in candidates:
        if candidate in RESTAURANT_CATEGORIES:
            return "restaurant"
    return None


def fetch_state_raw(state_abbr: str) -> list[dict]:
    bbox = STATE_BBOXES[state_abbr]
    bbox_str = ",".join(str(v) for v in bbox)
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
            out_path = tmp.name
        try:
            subprocess.run(
                [
                    sys.executable, "-m", "overturemaps", "download",
                    "--type=place", f"--bbox={bbox_str}", "-f", "geojson",
                    "-o", out_path,
                ],
                check=True, timeout=DOWNLOAD_TIMEOUT_SECONDS,
                capture_output=True, text=True,
            )
            with open(out_path) as f:
                return json.load(f).get("features", [])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(10 * attempt)
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)
    raise RuntimeError(f"Overture download for {state_abbr} failed: {last_error}")


def normalize_feature(feature: dict, state_abbr: str) -> dict | None:
    props = feature.get("properties", {})

    confidence = props.get("confidence")
    if confidence is not None and confidence < MIN_CONFIDENCE:
        return None

    category = classify_category(props.get("categories"))
    if category is None:
        return None

    name = (props.get("names") or {}).get("primary")
    if not name:
        return None

    addresses = props.get("addresses") or []
    addr0 = addresses[0] if addresses else {}
    address = (addr0.get("freeform") or "").strip()
    city = addr0.get("locality")
    if not city:
        return None

    geometry = feature.get("geometry") or {}
    coords = geometry.get("coordinates") or [None, None]
    lng, lat = coords[0], coords[1]

    zip_code = normalize_zip(addr0.get("postcode") or "")
    key = dedup_key(name, address, zip_code, lat=lat, lng=lng)
    if key is None:
        return None

    phones = props.get("phones") or []
    brand = ((props.get("brand") or {}).get("names") or {}).get("primary")

    return {
        "dedup_key": key,
        "name": name,
        "address": address or None,
        "city": city,
        "state": addr0.get("region") or state_abbr,
        "county": None,
        "zip_code": zip_code or None,
        "phone": phones[0] if phones else None,
        "category": category,
        "lat": lat,
        "lng": lng,
        "brand": brand,
        "source": SOURCE_NAME,
        "source_id": props.get("id") or feature.get("id"),
    }


def fetch_state(state_abbr: str) -> list[dict]:
    features = fetch_state_raw(state_abbr)
    records = []
    for feature in features:
        record = normalize_feature(feature, state_abbr)
        if record is not None:
            records.append(record)
    return records
