import base64
import json
import math
import os
import re

import requests
from lzstring import LZString

from src.immo_data import ImmoData, ReportType

BASE_URL = "https://www.immowelt.de"
SEARCH_URL = f"{BASE_URL}/classified-search"

_ESTATE_TYPES = {
    ReportType.HOUSE: "House,Apartment",
    ReportType.LAND: "Plot",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9",
}

_PLACE_ID_PREFIXES = ("POCODE", "AD08DE", "CITY", "MUNIC", "DISTRICT", "REGION", "COUNTRY")

_resolved_location: str | None = None
_resolved_coords: tuple[float, float] | None = None


def _encode_polyline(coords: list[tuple[float, float]]) -> str:
    def encode_val(v: float) -> str:
        n = int(round(v * 1e5))
        n = ~(n << 1) if n < 0 else n << 1
        chunks = []
        while n >= 0x20:
            chunks.append(chr((0x20 | (n & 0x1F)) + 63))
            n >>= 5
        chunks.append(chr(n + 63))
        return "".join(chunks)

    result = []
    prev_lat = prev_lng = 0.0
    for lat, lng in coords:
        result.append(encode_val(lat - prev_lat))
        result.append(encode_val(lng - prev_lng))
        prev_lat, prev_lng = lat, lng
    return "".join(result)


def _circle_polyline(lat: float, lng: float, radius_km: float, num_points: int = 32) -> str:
    R = 6378.137  # WGS84 equatorial radius
    d = radius_km / R
    lat_r = math.radians(lat)
    lng_r = math.radians(lng)
    pts = []
    for i in range(num_points):
        bearing = -2 * math.pi * i / num_points
        pt_lat = math.asin(
            math.sin(lat_r) * math.cos(d) + math.cos(lat_r) * math.sin(d) * math.cos(bearing)
        )
        pt_lng = lng_r + math.atan2(
            math.sin(bearing) * math.sin(d) * math.cos(lat_r),
            math.cos(d) - math.sin(lat_r) * math.sin(pt_lat),
        )
        pts.append((math.degrees(pt_lat), math.degrees(pt_lng)))
    pts.append(pts[0])
    return _encode_polyline(pts)


def _geocode(query: str) -> tuple[float, float] | None:
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "de"},
            headers={"User-Agent": "immo-scraper/1.0"},
            timeout=10,
        )
        results = r.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None


def _city_name_for_place_id(place_id: str) -> str | None:
    r = requests.get(
        f"{SEARCH_URL}?distributionTypes=Buy&estateTypes=House&locations={place_id}",
        headers=_HEADERS,
        timeout=15,
    )
    m = re.search(r"<title>[^<]+in ([^,<]+)", r.text)
    return m.group(1).strip() if m else None


def _build_location_param(place_id: str) -> str:
    radius_str = os.getenv("RADIUS")
    if not radius_str or _resolved_coords is None:
        return place_id
    radius = int(radius_str)
    lat, lng = _resolved_coords
    location = {
        "placeId": place_id,
        "radius": radius,
        "polyline": _circle_polyline(lat, lng, radius),
        "coordinates": {"lat": lat, "lng": lng},
    }
    return base64.urlsafe_b64encode(
        json.dumps(location, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()


def get_immowelt_results():
    return _get_results_of_type(ReportType.HOUSE), _get_results_of_type(ReportType.LAND)


def _get_results_of_type(type: ReportType) -> list[ImmoData]:
    global _resolved_location, _resolved_coords
    if _resolved_location is None:
        _resolved_location, _resolved_coords = _resolve_location(os.getenv("LOCATION", ""))

    listings = []
    page = 1

    while True:
        url = (
            f"{SEARCH_URL}"
            f"?distributionTypes=Buy,Buy_Auction,Compulsory_Auction"
            f"&estateTypes={_ESTATE_TYPES[type]}"
            f"&locations={_build_location_param(_resolved_location)}"
            f"&page={page}"
        )
        print(url)

        page_data = _get_page_data(url)
        if page_data is None:
            break

        classified_ids = page_data.get("classifieds", [])
        classifieds_data = page_data.get("classifiedsData", {})

        new_listings = [
            _get_immo_data(type, classifieds_data[cid])
            for cid in classified_ids
            if cid in classifieds_data
        ]
        listings += [x for x in new_listings if x is not None]

        total_count = page_data.get("totalCount", 0)
        if len(listings) >= total_count or not classified_ids:
            break
        page += 1

    return listings


def _resolve_location(location: str) -> tuple[str, tuple[float, float] | None]:
    """Return (place_id, coords) where coords is (lat, lng) or None.

    Coords are only fetched when RADIUS is set, since they're only needed for
    the radius search polyline.
    """
    needs_coords = bool(os.getenv("RADIUS"))

    if any(location.upper().startswith(p) for p in _PLACE_ID_PREFIXES):
        place_id = location
        if needs_coords:
            city = _city_name_for_place_id(place_id)
            coords = _geocode(city) if city else None
        else:
            coords = None
        return place_id, coords

    slug = _slugify(location)
    r = requests.get(
        f"{BASE_URL}/liste/{slug}/haeuser/kaufen",
        headers=_HEADERS,
        timeout=15,
        allow_redirects=True,
    )

    if "fgtauth" in r.text or "captive" in r.url:
        raise ValueError(
            f"A captive portal is intercepting network traffic (detected: {r.url}). "
            f"Authenticate via your browser first, or set LOCATION to a place ID directly "
            f"(e.g. 'AD08DE2812' for Künzell)."
        )

    m = re.search(r"/(ad08de[0-9a-f]{4,8})(?:[?#/]|$)", r.url, re.IGNORECASE)
    if m:
        place_id = m.group(1).upper()
        coords = _geocode(location) if needs_coords else None
        return place_id, coords

    raise ValueError(
        f"Could not resolve location '{location}' to an immowelt place ID. "
        f"Set LOCATION to a valid ID (e.g. 'POCODE2604' or 'AD08DE2812') "
        f"or a German city name (e.g. 'Künzell')."
    )


def _slugify(text: str) -> str:
    text = text.lower()
    for umlaut, replacement in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
        text = text.replace(umlaut, replacement)
    text = text.replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]", "", text)
    return text


def _get_page_data(url: str) -> dict | None:
    response = requests.get(url, headers=_HEADERS, timeout=30)
    if not response.ok:
        return None

    m = re.search(
        r'<script[^>]*id="__UFRN_FETCHER__"[^>]*>(.*?)</script>',
        response.text,
        re.DOTALL,
    )
    if not m:
        return None

    inner = re.search(r'JSON\.parse\("(.+)"\);', m.group(1).strip(), re.DOTALL)
    if not inner:
        return None

    json_str = inner.group(1).encode().decode("unicode_escape")
    data = json.loads(json_str)
    serp_raw = data.get("data", {}).get("classified-serp-init-data")
    if not serp_raw:
        return None

    parsed = json.loads(LZString().decompressFromBase64(serp_raw))
    return parsed.get("pageProps")


def _get_immo_data(type: ReportType, listing: dict) -> ImmoData | None:
    try:
        title = listing["hardFacts"]["title"]
        price = listing["hardFacts"]["price"]["ariaLabel"]
        url = listing["url"]

        living_area = None
        land_area = None
        for fact in listing["hardFacts"].get("facts", []):
            if fact["type"] == "livingSpace":
                living_area = fact["splitValue"]
            elif fact["type"] == "plotSpace":
                land_area = fact["splitValue"]

        return ImmoData(
            link=url,
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            type=type,
            distance=None,
        )
    except Exception:
        return None
