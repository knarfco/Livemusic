"""Phase 1 nationwide source: OpenStreetMap's free Overpass API.

Queried one state at a time (not one giant national query) to stay well
within Overpass's fair-use limits, with a short delay between states.
"""

import time
import requests

from normalize import dedup_key, normalize_zip

# Public Overpass mirrors, tried in order -- overpass-api.de rejects
# requests that don't identify themselves (406) or that hit it too hard
# (429/504); a real User-Agent fixes the first, and falling back to another
# mirror covers the rest without needing anyone to notice or intervene.
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
)
REQUEST_HEADERS = {
    "User-Agent": "AreaBandsVenueImportBot/1.0 (https://areabands.com; free venue-listing data pipeline)"
}
AMENITIES = ("bar", "pub", "restaurant", "cafe", "fast_food")
DELAY_BETWEEN_STATES_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 200
MAX_RETRIES = 3

# ISO 3166-2 codes for the 50 states + DC -- what Overpass's area["ISO3166-2"]
# filter expects, prefixed with "US-".
STATE_ABBREVIATIONS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
]

AMENITY_TO_CATEGORY = {
    "bar": "bar",
    "pub": "bar",
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "fast_food": "restaurant",
}


def build_query(state_abbr: str) -> str:
    amenity_pattern = "|".join(AMENITIES)
    return f"""
    [out:json][timeout:180];
    area["ISO3166-2"="US-{state_abbr}"]["admin_level"="4"]->.searchArea;
    (
      node["amenity"~"^({amenity_pattern})$"](area.searchArea);
      way["amenity"~"^({amenity_pattern})$"](area.searchArea);
    );
    out center tags;
    """


def fetch_state_raw(state_abbr: str) -> list[dict]:
    query = build_query(state_abbr)
    last_error = None
    got_empty_200 = False
    for url in OVERPASS_URLS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    url, data=query, headers=REQUEST_HEADERS,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                if resp.status_code == 200:
                    elements = resp.json().get("elements", [])
                    if elements:
                        return elements
                    # A whole US state legitimately having zero bars/restaurants
                    # is implausible -- more likely this mirror's area index for
                    # this state is stale or missing (a real, silent failure
                    # mode we hit for South Carolina). Try another mirror
                    # before accepting an empty result.
                    got_empty_200 = True
                    last_error = f"200 OK but zero elements from {url}"
                    time.sleep(10 * attempt)
                    continue
                if resp.status_code in (406, 429, 504):
                    last_error = f"HTTP {resp.status_code} from {url}"
                    time.sleep(10 * attempt)
                    continue
                resp.raise_for_status()
            except requests.RequestException as exc:
                last_error = f"{exc} ({url})"
                time.sleep(10 * attempt)
    if got_empty_200:
        print(f"[{state_abbr}] WARNING: every mirror returned zero elements ({last_error})")
        return []
    raise RuntimeError(
        f"Overpass fetch for {state_abbr} failed on every mirror: {last_error}"
    )


def normalize_element(el: dict, state_abbr: str) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name")
    city = tags.get("addr:city")
    if not name or not city:
        return None

    housenumber = tags.get("addr:housenumber", "")
    street = tags.get("addr:street", "")
    address = f"{housenumber} {street}".strip()
    if not address:
        return None

    zip_code = normalize_zip(tags.get("addr:postcode", ""))
    key = dedup_key(name, address, zip_code)
    if key is None:
        return None

    if el["type"] == "way":
        center = el.get("center", {})
        lat, lng = center.get("lat"), center.get("lon")
    else:
        lat, lng = el.get("lat"), el.get("lon")

    amenity = tags.get("amenity")
    return {
        "dedup_key": key,
        "name": name,
        "address": address,
        "city": city,
        "state": tags.get("addr:state") or state_abbr,
        "county": tags.get("addr:county"),
        "zip_code": zip_code or None,
        "phone": tags.get("contact:phone") or tags.get("phone"),
        "category": AMENITY_TO_CATEGORY.get(amenity, "food_and_drink"),
        "lat": lat,
        "lng": lng,
        "brand": tags.get("brand"),
        "source": "osm",
        "source_id": f"{el['type']}/{el['id']}",
    }


def fetch_state(state_abbr: str) -> list[dict]:
    elements = fetch_state_raw(state_abbr)
    records = []
    for el in elements:
        record = normalize_element(el, state_abbr)
        if record is not None:
            records.append(record)
    return records
