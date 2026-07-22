from typing import Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import src.browser as browser
from src.immo_data import ImmoData, ReportType

BASE_URL = "https://v-r-immobilien.de"
URL = "https://v-r-immobilien.de/immobilien/?quick-erwerbsart=buy&quick-objektarten=***&quick-orte=$$$"
LOCATIONS = ["Fulda", "Künzell", "Petersberg", "Eichenzell", "Hofbieber", "Dipperz"]

driver = None


class _BlockedException(Exception):
    pass


def get_vr_immobilien_results():
    global driver
    try:
        house_listings = _get_results_of_type(ReportType.HOUSE)
        land_listings = _get_results_of_type(ReportType.LAND)
        if driver is not None:
            browser.save_cookies(driver, "vr_immobilien")
        return house_listings, land_listings
    except _BlockedException:
        print("VR Immobilien blocked — run 'python main.py --setup vr_immobilien' to refresh session")
        return [], []
    finally:
        if driver is not None:
            driver.quit()
            driver = None


def _get_results_of_type(type: ReportType) -> list[ImmoData]:
    listings = []
    url = _get_url_for_type(type)
    for location in LOCATIONS:
        location_url = _get_url_for_location(url, location)
        print(location_url)
        soup = _get_soup(location_url)
        if soup is None:
            break
        new_listings = soup.find_all("div", {"class": "mw-object-col"})
        if not new_listings:
            break
        listings += [(listing, location) for listing in new_listings]
    return list(filter(lambda x: x is not None, map(lambda x: _get_immo_data(type, x[0], city=x[1]), listings)))


def _get_url_for_type(type: ReportType):
    object_type = "house" if type == ReportType.HOUSE else "plot"
    return URL.replace("***", object_type, 1)


def _get_url_for_location(url: str, location: str) -> str:
    return url.replace("$$$", location, 1)


def _get_soup(url) -> Optional[BeautifulSoup]:
    global driver
    if driver is None:
        driver = browser.get_driver(headless=True)
        browser.load_cookies(driver, "vr_immobilien", BASE_URL)
    try:
        driver.get(url)
    except WebDriverException:
        return None
    if not browser.wait_for_element(driver, By.CLASS_NAME, "mw-object-list-view-wrapper", timeout=10):
        raise _BlockedException()
    return BeautifulSoup(driver.page_source, "html.parser")


def _get_immo_data(type: ReportType, listing, city: str | None = None) -> Optional[ImmoData]:
    try:
        title_elem = listing.find("div", {"class": "mw-object-col-title"})
        if not title_elem:
            return None
        title = title_elem.text.strip()
        link_elem = listing.find("a", {"class": "mw-paginated-prop-anker-click"})
        if not link_elem or "href" not in link_elem.attrs:
            return None
        link = link_elem["href"]
        price_elem = listing.find("div", {"class": "mw-object-col-details-price-number"})
        if not price_elem:
            return None
        price = price_elem.text.strip()
        living_area = None
        living_area_container = listing.find("div", {"data-current-type": "wohnflaeche"})
        if living_area_container:
            elem = living_area_container.find("div", {"class": "mw-object-col-details-info-col-number"})
            if elem:
                living_area = elem.text.strip()
        land_area = None
        land_area_container = listing.find("div", {"data-current-type": "grundstuecksfl"})
        if land_area_container:
            elem = land_area_container.find("div", {"class": "mw-object-col-details-info-col-number"})
            if elem:
                land_area = elem.text.strip()
        return ImmoData(
            link=link, title=title, price=price,
            living_area=living_area, land_area=land_area,
            type=type, distance=None, location=city,
        )
    except Exception as e:
        print(f"Error extracting immo data: {e}")
        return None
