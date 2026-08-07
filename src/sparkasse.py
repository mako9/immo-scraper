import os
import re
import time
from typing import Optional
from urllib.parse import urlencode

import requests

from src.immo_data import ImmoData, ReportType

BASE_URL = "https://www.sparkasse-fulda.de"
SEARCH_URL = f"{BASE_URL}/de/home/privatkunden/immobilien/immobilie-kaufen.html"

_ESTATE_TYPE_GROUPINGS = {
    ReportType.HOUSE: 396,
    ReportType.LAND: 397,
}
_SALES_OFFER_TYPE = 2


def get_sparkasse_results():
    """Return tuple (house_listings, land_listings)."""
    location = os.getenv("LOCATION")
    zip_code = os.getenv("ZIP_CODE")
    max_price = os.getenv("PRICE_UPPER_LIMIT")

    # Use LOCATION if available, otherwise fallback to ZIP code
    search_location = location if location else zip_code

    radius_km = os.getenv("RADIUS")
    if radius_km is not None:
        try:
            radius_km = int(radius_km)
        except Exception:
            radius_km = None

    proxy_url = _get_proxy_url()
    if proxy_url is None:
        print("No Sparkasse API proxy found.")
        return [], []

    coordinates = _resolve_location(proxy_url, search_location)
    if search_location and coordinates is None:
        print(f"Could not resolve Sparkasse location: {search_location}")
        return [], []

    house_listings = _get_results_of_type(
        ReportType.HOUSE,
        proxy_url=proxy_url,
        coordinates=coordinates,
        radius_km=radius_km,
        max_price=max_price,
    )
    land_listings = _get_results_of_type(
        ReportType.LAND,
        proxy_url=proxy_url,
        coordinates=coordinates,
        radius_km=radius_km,
        max_price=max_price,
    )

    return house_listings, land_listings


def _get_proxy_url() -> Optional[str]:
    print("Fetching API from", SEARCH_URL)
    try:
        resp = requests.get(
            SEARCH_URL,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible)"},
        )
        if resp.status_code == 200:
            m = re.search(r'data-sip-api-proxy\s*=\s*"([^"]+)"', resp.text)
            if m:
                proxy_attr = m.group(1)
                return (
                    proxy_attr if proxy_attr.startswith("http") else BASE_URL + proxy_attr
                )
    except Exception:
        pass
    return None


def _resolve_location(
    proxy_url: str, location: Optional[str]
) -> Optional[tuple[float, float]]:
    if not location:
        return None

    route = f"immobilien-api/locations?{urlencode({'pattern': location, 'limit': 1})}"
    response = _post_api_request(proxy_url, {"route": route})
    if not isinstance(response, list):
        return None

    for candidate in response:
        try:
            return float(candidate["latitude"]), float(candidate["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _get_results_of_type(
    type: ReportType,
    proxy_url: str,
    coordinates: Optional[tuple[float, float]] = None,
    radius_km: Optional[int] = None,
    max_price: Optional[str] = None,
) -> list[ImmoData]:
    """Collect listings for the given ReportType using the current site API."""
    listings = []
    page = 1
    size = 10

    while True:
        route = _build_estates_route(
            type, page, size, coordinates, radius_km, max_price
        )
        print("API request", proxy_url, "page", page, "route", route)
        estates_resp = _post_api_request(
            proxy_url, {"route": route, "return_data": "react_frontend"}
        )
        if not isinstance(estates_resp, dict):
            break

        estates = estates_resp.get("estates", [])
        if not estates:
            break

        listings.extend(estates)
        page_count = estates_resp.get("pageCount", 1)
        try:
            page_count = int(page_count)
        except (TypeError, ValueError):
            page_count = 1
        if page >= page_count:
            break
        page += 1

    return [
        listing
        for estate in listings
        if (listing := _get_immo_data_from_api(type, estate)) is not None
    ]


def _build_estates_route(
    type: ReportType,
    page: int,
    size: int,
    coordinates: Optional[tuple[float, float]],
    radius_km: Optional[int],
    max_price: Optional[str],
) -> str:
    params = {
        "estateTypeGroupingIds": _ESTATE_TYPE_GROUPINGS[type],
        "offerType": _SALES_OFFER_TYPE,
        "offererCategoryConfig": "53050180",
        "page": page,
        "pageSize": size,
    }
    if coordinates is not None:
        latitude, longitude = coordinates
        params["latitude"] = latitude
        params["longitude"] = longitude
    if radius_km is not None:
        params["radius"] = radius_km
    if max_price:
        params["maxPrice"] = max_price
    return f"immobilien-api/estates?{urlencode(params)}"

def _post_api_request(proxy_url: str, body: dict) -> Optional[dict | list]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible)", "Content-Type": "application/json"}
    for attempt in range(8):
        try:
            resp = requests.post(proxy_url, json=body, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            response = resp.json()
            if isinstance(response, dict) and "pending" in response:
                time.sleep(0.2 * (attempt + 1))
                continue
            return response
        except Exception as error:
            print("API request attempt", attempt + 1, "failed, retrying...", error)
            return None
    return None


def _get_immo_data_from_api(type: ReportType, listing) -> Optional[ImmoData]:
    """Convert an estate dict from the API into ImmoData."""
    try:
        est = listing[0] if isinstance(listing, (list, tuple)) else listing

        title = est.get("title") or est.get("headline", "")

        eid = est.get("id")
        link = None
        if eid:
            detail_page = (
                f"{BASE_URL}/de/home/privatkunden/immobilien/detailansicht.html"
            )
            link = f"{detail_page}?eid={eid}"

        price = (est.get("priceData") or {}).get("value")
        living_area = None
        land_area = None

        for fact in est.get("mainFacts") or est.get("main_facts", []) or []:
            label = (fact.get("name") or fact.get("label") or "").lower()
            value = fact.get("value", "")
            if "kaufpreis" in label and not price:
                price = value
            if "livingspace" in label or "wohnfl" in label:
                # Extract numeric value from "150 m²" format
                m = re.search(r"([\d\.,]+)", value)
                if m:
                    living_area = _parse_number(m.group(1))
            elif "propertysize" in label or "grundst" in label:
                m = re.search(r"([\d\.,]+)", value)
                if m:
                    land_area = _parse_number(m.group(1))

        location = est.get("subtitle") or est.get("geo_label") or None

        return ImmoData(
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            link=link,
            type=type,
            distance=None,
            location=location,
        )
    except Exception:
        return None


def _parse_number(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,\.]", "", text)
    return cleaned if cleaned != "" else None
