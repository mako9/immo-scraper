from typing import Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from src.immo_data import ImmoData, ReportType

BASE_URL = "https://v-r-immobilien.de"
URL = "https://v-r-immobilien.de/immobilien/?quick-erwerbsart=buy&quick-objektarten=***&quick-orte=$$$"
LOCATIONS = ["Fulda", "Künzell", "Petersberg", "Eichenzell", "Hofbieber", "Dipperz"]

driver = None


def get_vr_immobilien_results():
    house_listings = _get_results_of_type(ReportType.HOUSE)
    land_listings = _get_results_of_type(ReportType.LAND)

    if driver is not None:
        driver.quit()

    return house_listings, land_listings


def _get_results_of_type(type: ReportType):
    """Fetch all listings of a specific type (HOUSE or LAND)"""
    listings = []
    url = _get_url_for_type(type)

    for location in LOCATIONS:
        location_url = _get_url_for_location(url, location)

        print(location_url)
        soup = _get_soup(location_url)

        if soup is None:
            break

        # Find all listing containers - looking for mw-object-col divs with kauf (buy) or miete (rent) class
        new_listings = soup.find_all("div", {"class": "mw-object-col"})

        if not new_listings:
            break

        listings += new_listings

    return list(
        filter(
            lambda x: x is not None, map(lambda x: _get_immo_data(type, x), listings)
        )
    )


def _get_url_for_type(type: ReportType):
    """Get the base URL with the correct object type parameter"""
    object_type = "house" if type == ReportType.HOUSE else "plot"
    return URL.replace("***", object_type, 1)


def _get_url_for_location(url: str, location: str) -> str:
    """Get the URL with the correct location parameter"""
    return url.replace("$$$", location, 1)


def _get_soup(url) -> Optional[BeautifulSoup]:
    """Fetch and parse the HTML content"""
    global driver

    if driver is None:
        service = Service()
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=service, options=options)

    driver.get(url)
    wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds

    # Wait for property listings to load
    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "mw-object-list-view-wrapper")
            )
        )
    except TimeoutException:
        print(f"Timeout while loading page: {url}")
        return None

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    return soup


def _get_immo_data(type: ReportType, listing) -> Optional[ImmoData]:
    """Extract ImmoData from a listing element"""
    try:
        # Get title from the listing - inside mw-object-col-title div
        title_elem = listing.find("div", {"class": "mw-object-col-title"})
        if not title_elem:
            return None
        title = title_elem.text.strip()

        # Get link from the anchor tag
        link_elem = listing.find("a", {"class": "mw-paginated-prop-anker-click"})
        if not link_elem or "href" not in link_elem.attrs:
            return None
        link = link_elem["href"]

        # Get price from mw-object-col-details-price-number
        price_elem = listing.find(
            "div", {"class": "mw-object-col-details-price-number"}
        )
        if not price_elem:
            return None
        price = price_elem.text.strip()

        # Get living area (Wohnfläche) - look for div with data-current-type="wohnflaeche"
        living_area = None
        living_area_container = listing.find(
            "div", {"data-current-type": "wohnflaeche"}
        )
        if living_area_container:
            living_area_elem = living_area_container.find(
                "div", {"class": "mw-object-col-details-info-col-number"}
            )
            if living_area_elem:
                living_area = living_area_elem.text.strip()

        # Get land area (Grundstücksfläche) - look for div with data-current-type="grundstuecksfl"
        land_area = None
        land_area_container = listing.find(
            "div", {"data-current-type": "grundstuecksfl"}
        )
        if land_area_container:
            land_area_elem = land_area_container.find(
                "div", {"class": "mw-object-col-details-info-col-number"}
            )
            if land_area_elem:
                land_area = land_area_elem.text.strip()

        return ImmoData(
            link=link,
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            type=type,
            distance=None,
        )
    except Exception as e:
        print(f"Error extracting immo data: {e}")
        return None
