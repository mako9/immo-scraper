import argparse
import os
import re
import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()

from src.immo_data import ImmoData
from src.immo_platform import ImmoPlatform
from src.immowelt import get_immowelt_results
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


_SETUP_PLATFORMS = {
    "immoscout": {
        "url": "https://www.immobilienscout24.de",
        "env_key": "IMMOSCOUT_ENABLED",
    },
    "vr_immobilien": {
        "url": "https://v-r-immobilien.de",
        "env_key": "VR_IMMOBILIEN_ENABLED",
    },
    "kleinanzeigen": {
        "url": "https://www.kleinanzeigen.de",
        "env_key": "KLEINANZEIGEN_ENABLED",
    },
}


def _run_setup(platforms: list[str]) -> None:
    import src.browser as browser
    from selenium.webdriver.common.by import By
    for platform in platforms:
        cfg = _SETUP_PLATFORMS[platform]
        print(f"Setting up {platform} — solve the captcha in the browser window, then wait...")
        drv = browser.get_driver(headless=False)
        browser.load_cookies(drv, platform, cfg["url"])
        drv.get(cfg["url"])
        browser.wait_for_element(drv, By.TAG_NAME, "body", timeout=300)
        browser.save_cookies(drv, platform)
        drv.quit()
        print(f"Cookies saved for {platform}.")


def _load_and_store_data():
    house_listings, land_listings = _get_results()
    calculate_rating(house_listings)
    calculate_rating(land_listings)
    house_listings = _sort_listings(house_listings)
    land_listings = _sort_listings(land_listings)

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


def _sort_listings(listings: list) -> list:
    unrated = [l for l in listings if l.rating is None]
    rated = sorted(
        [l for l in listings if l.rating is not None],
        key=lambda listing: (listing.type.name, listing.rating, listing.ratio),
        reverse=True,
    )
    return unrated + rated


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
        if item.price and (item.living_area or item.land_area):
            key = (item.price, item.living_area, item.land_area)
        else:
            key = (item.title, item.price, item.land_area)
        if key not in seen:
            seen[key] = item
    return set(seen.values())


def _get_result_for_platform(
    platform: ImmoPlatform,
) -> tuple[list[ImmoData], list[ImmoData]]:
    env = os.getenv(f"{platform.value}_ENABLED")
    if env != "true":
        print(f"Skipping {platform.value} as it is not enabled")
        return [], []

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

parser = argparse.ArgumentParser()
parser.add_argument(
    "--setup",
    nargs="?",
    const="all",
    choices=["immoscout", "vr_immobilien", "kleinanzeigen", "all"],
    help="Run one-time captcha setup for a platform (or all enabled ones)",
)
args = parser.parse_args()

if args.setup:
    platforms = (
        [p for p, cfg in _SETUP_PLATFORMS.items() if os.getenv(cfg["env_key"]) == "true"]
        if args.setup == "all"
        else [args.setup]
    )
    _run_setup(platforms)
else:
    _load_and_store_data()
