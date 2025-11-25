import os
from dotenv import load_dotenv

from src.immo_platform import ImmoPlatform
from src.immowelt import get_immowelt_results
from src.immonet import get_immonet_results
from src.immoscout import get_immoscout_results
from src.kleinanzeigen import get_kleinanzeigen_results
from src.vr_immobilien import get_vr_immobilien_results
from src.rating import calculate_rating
from src.xls import write_listings


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


def _get_results():
    house_listings = []
    land_listings = []
    for platform in ImmoPlatform:
        houses, lands = _get_result_for_platform(platform)
        house_listings += houses
        land_listings += lands

    return set(filter(lambda l: l is not None, house_listings)), set(
        filter(lambda l: l is not None, land_listings)
    )


def _get_result_for_platform(platform: ImmoPlatform):
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


# Load the environment variables from the .env file
load_dotenv()
# Load and store data in .xls file
_load_and_store_data()
