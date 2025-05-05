from typing import Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from src.url import get_url_without_page, get_url_with_page
from src.immo_data import ImmoData, ReportType
from src.immo_platform import ImmoPlatform

BASE_URL = "https://www.immobilienscout24.de"
URL = "https://www.immobilienscout24.de/Suche/radius/+++?centerofsearchaddress=Fulda%20(Kreis);;;1276007005017;;***&geocoordinates=50.54398;9.7184;§§§.0&enteredFrom=one_step_search&pagenumber=$$$&price=-###"

executor_url: str = None
session_id: str = None
driver = None


def get_immoscout_results():
    house_listings = _get_results_of_type(ReportType.HOUSE)
    land_listings = _get_results_of_type(ReportType.LAND)

    driver.quit()

    return house_listings, land_listings


def _get_url_without_page(type: ReportType):
    return get_url_without_page(URL, ImmoPlatform.IMMOSCOUT, type)


def _get_results_of_type(type: ReportType):
    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)

    index = 1
    while True:
        url = get_url_with_page(url_without_page, index)
        print(url)
        soup = _get_soup(url, By.ID, "result-list-content")
        new_listings = soup.find_all("div", {"class": "listing-card"})
        listings += list(
            map(
                lambda x: (
                    x,
                    _get_listing_soup(x),
                ),
                new_listings,
            )
        )
        if len(new_listings) < 20:
            break
        index += 1

    return list(
        filter(
            lambda x: x is not None, map(lambda x: _get_immo_data(type, x), listings)
        )
    )


def _get_listing_soup(listing):
    href = _get_href(listing)
    if href is None:
        return None
    return _get_soup(f"{BASE_URL}{href}", By.CLASS_NAME, "main-criteria-container")


def _get_soup(url, type, name):
    global driver  # Declare the variables as nonlocal
    # Send the request and get the HTML response
    if driver is None:
        service = Service()
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 60)  # Wait up to 60 seconds

    # Once we need to accept manually the Captcha. The browser session will then be reused.

    wait.until(EC.presence_of_element_located((type, name)))

    html = driver.page_source

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    return soup


def _get_immo_data(type, listing):
    infos = listing[0].findAll("dd", {"class": "font-bold"})
    if not infos:
        return None
    price = infos[0].text.strip()
    living_area = None
    if type == ReportType.HOUSE:
        living_area = infos[1].text.strip()
        land_area = infos[3].text.strip() if len(infos) > 3 else None
    else:
        land_area = infos[1].text.strip()

    return ImmoData(
        link=BASE_URL + _get_href(listing[0]),
        title=listing[0].find("h2", {"data-testid": "headline"}).text.strip(),
        price=price,
        living_area=living_area,
        land_area=land_area,
        type=type,
        distance=None,
    )


def _get_href(listing) -> Optional[str]:
    element = listing.find("a")
    if element:
        return element["href"]
