import os
import re
from dotenv import load_dotenv

from src.immo_data import ImmoData
from src.immo_platform import ImmoPlatform
from src.immowelt import get_immowelt_results
from src.immonet import get_immonet_results
from src.immoscout import get_immoscout_results
from src.kleinanzeigen import get_kleinanzeigen_results
from src.vr_immobilien import get_vr_immobilien_results
from src.sparkasse import get_sparkasse_results
from src.rating import calculate_rating
from src.xls import write_listings


BLACKLISTED_KEYWORDS = ["Bien-Zenker", "Unser WOHLFÜHLSERVICE", "MASSA"]

_BLACKLIST_PATTERN = re.compile(
    "|".join(map(re.escape, BLACKLISTED_KEYWORDS)),
    re.IGNORECASE,
)


def _load_and_store_data():
    house_listings, land_listings = _get_results()
    calculate_rating(house_listings)
    calculate_rating(land_listings)
    house_listings = sorted(
        house_listings,
        key=lambda listing: (listing.type.name, listing.rating, listing.ratio),
        reverse=True,
    )
    land_listings = sorted(
        land_listings,
        key=lambda listing: (listing.type.name, listing.rating, listing.ratio),
        reverse=True,
    )

    print(
        f"Found {len(house_listings)} house listings and {len(land_listings)} land listings"
    )

    write_listings(house_listings, land_listings)


def _get_results() -> tuple[set[ImmoData], set[ImmoData]]:
    house_listings = []
    land_listings = []
    for platform in ImmoPlatform:
        houses, lands = _get_result_for_platform(platform)
        house_listings += houses
        land_listings += lands

    return _cleanup_results(house_listings), _cleanup_results(land_listings)


def _cleanup_results(listings: list[ImmoData]) -> set[ImmoData]:
    return _deduplicate_results(
        {
            listing
            for listing in listings
            if listing
            and listing.title
            and not _BLACKLIST_PATTERN.search(listing.title)
        }
    )


def _deduplicate_results(data: set[ImmoData]) -> set[ImmoData]:
    seen = {}
    for item in data:
        key = (item.title, item.price, item.land_area)
        if key not in seen:
            seen[key] = item
    return set(seen.values())


def _get_result_for_platform(
    platform: ImmoPlatform,
) -> tuple[list[ImmoData], list[ImmoData]]:
    env = os.getenv(platform.value)
    if env != "active":
        print(f"Skipping {platform.value} as it is set to {env}")
        return [], []

    if platform == ImmoPlatform.IMMONET:
        return get_immonet_results()
    if platform == ImmoPlatform.IMMOSCOUT:
        return get_immoscout_results()
    if platform == ImmoPlatform.IMMOWELT:
        return get_immowelt_results()
    if platform == ImmoPlatform.KLEINANZEIGEN:
        return get_kleinanzeigen_results()
    if platform == ImmoPlatform.VR_IMMOBILIEN:
        return get_vr_immobilien_results()
    if platform == ImmoPlatform.SPARKASSE:
        return get_sparkasse_results()


# Load the environment variables from the .env file
load_dotenv()
# Load and store data in .xls file
_load_and_store_data()
