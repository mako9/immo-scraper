import os
import re
from typing import Optional

import requests

from src.immo_data import ImmoData, ReportType

BASE_URL = "https://www.sparkasse-fulda.de"
SEARCH_URL = f"{BASE_URL}/de/home/privatkunden/immobilien/immobilie-kaufen.html"


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

    house_listings = _get_results_of_type(
        ReportType.HOUSE,
        location=search_location,
        radius_km=radius_km,
        max_price=max_price,
    )
    land_listings = _get_results_of_type(
        ReportType.LAND,
        location=search_location,
        radius_km=radius_km,
        max_price=max_price,
    )

    return house_listings, land_listings


def _get_results_of_type(
    type: ReportType,
    location: Optional[str] = None,
    radius_km: Optional[int] = None,
    max_price: Optional[str] = None,
):
    """Collect listings for the given ReportType using the site's API."""
    listings = []

    # Try API first
    print("Fetching API from", SEARCH_URL)
    proxy_attr = None
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
    except Exception:
        pass

    zip_city_estate_id = None
    perimeter = None
    if proxy_attr:
        proxy_url = (
            proxy_attr if proxy_attr.startswith("http") else BASE_URL + proxy_attr
        )

        if location:
            zip_city_estate_id = location
            if radius_km is not None:
                perimeter = int(radius_km)

        page = 1
        size = 10  # Initial size, will be updated from API response
        pages_fetched = 0

        while True:
            pages_fetched += 1

            print(
                "API request",
                proxy_url,
                "page",
                page,
                "location",
                zip_city_estate_id,
                "perimeter",
                perimeter,
                "max_price",
                max_price,
            )
            estates_resp = _fetch_estates_via_api(
                proxy_url, page, size, type, zip_city_estate_id, perimeter, max_price
            )
            if not estates_resp:
                break

            # Update page size from response for subsequent requests
            if "page_size" in estates_resp:
                size = estates_resp["page_size"]

            estates = estates_resp.get("_embedded", {}).get("estate", [])
            if not estates:
                # Fallback to old format for compatibility
                estates = estates_resp.get("estates", [])
            if not estates:
                break

            page_count = estates_resp.get("page_count") or 1
            try:
                page_count = int(page_count)
            except Exception:
                page_count = 1

            for estate in estates:
                listings.append((estate, None))

            # Stop if we've processed all pages
            if page >= page_count:
                break
            page += 1

        # Map API estate dicts to ImmoData
        results = list(
            filter(None, map(lambda e: _get_immo_data_from_api(type, e), listings))
        )
        if results:
            return results

    print("No API results found.")
    return []


def _fetch_estates_via_api(
    proxy_url: str,
    page: int,
    size: int,
    type: ReportType,
    zip_city_estate_id: Optional[str] = None,
    radius: Optional[int] = None,
    max_price: Optional[str] = None,
):
    """Request estates from the site's proxy API and return parsed JSON or None"""
    body = {
        "route": "estate",
        "return_data": "teaser_list",
        "page": page,
        "limit": size,
    }

    if zip_city_estate_id:
        body["zip_city_estate_id"] = zip_city_estate_id
    if radius is not None:
        body["perimeter"] = int(radius)
    if max_price:
        body["max_price"] = max_price

    body["marketing_type"] = "buy"
    body["usage_type"] = "residential"
    body["estate_type"] = "house" if type == ReportType.HOUSE else "property"
    body["sort_by"] = "institute_asc"
    body["regio_client_id"] = "53050180"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible)",
        "Content-Type": "application/json",
    }

    for attempt in range(8):
        try:
            resp = requests.post(proxy_url, json=body, headers=headers, timeout=15)
            if resp.status_code != 200:
                return None
            j = resp.json()
            if "pending" in j:
                # wait and retry
                time_to_wait = 0.2 * (attempt + 1)
                try:
                    import time

                    time.sleep(time_to_wait)
                except Exception:
                    pass
                continue
            return j
        except Exception as e:
            print("API request attempt", attempt + 1, "failed, retrying...", e)
            return None
    return None


def _get_immo_data_from_api(type: ReportType, listing) -> Optional[ImmoData]:
    """Convert an estate dict from the API into ImmoData."""
    try:
        est = listing[0] if isinstance(listing, (list, tuple)) else listing

        title = est.get("headline") or est.get("title", "")

        eid = est.get("id")
        link = None
        if eid:
            detail_page = (
                f"{BASE_URL}/de/home/privatkunden/immobilien/detailansicht.html"
            )
            link = f"{detail_page}?eid={eid}"

        price = None
        living_area = None
        land_area = None

        for fact in est.get("main_facts", []) or []:
            label = fact.get("label", "").lower()
            value = fact.get("value", "")
            if "kaufpreis" in label:
                price = value
            if "wohnfl" in label:
                # Extract numeric value from "150 m²" format
                m = re.search(r"([\d\.,]+)", value)
                if m:
                    living_area = _parse_number(m.group(1))
            elif "grundst" in label:
                m = re.search(r"([\d\.,]+)", value)
                if m:
                    land_area = _parse_number(m.group(1))

        return ImmoData(
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            link=link,
            type=type,
            distance=None,  # TODO: calculate from lat/lng
        )
    except Exception:
        return None


def _parse_number(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,\.]", "", text)
    return cleaned if cleaned != "" else None
