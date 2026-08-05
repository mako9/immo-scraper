from typing import Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import src.browser as browser
from src.url import get_url_without_page, get_url_with_page
from src.immo_data import ImmoData, ReportType
from src.immo_platform import ImmoPlatform

BASE_URL = "https://www.immobilienscout24.de"
URL = "https://www.immobilienscout24.de/Suche/radius/+++?centerofsearchaddress=Fulda%20(Kreis);;;1276007005017;;***&geocoordinates=50.54398;9.7184;§§§.0&enteredFrom=one_step_search&pagenumber=$$$&price=-###"

driver = None
was_blocked = False


class _BlockedException(Exception):
    pass


def get_immoscout_results():
    global driver, was_blocked
    was_blocked = False
    try:
        house_listings = _get_results_of_type(ReportType.HOUSE)
        land_listings = _get_results_of_type(ReportType.LAND)
        if driver is not None:
            browser.save_cookies(driver, "immoscout")
        return house_listings, land_listings
    except _BlockedException:
        was_blocked = True
        print("IS24 blocked — run 'python main.py --setup immoscout' to refresh session")
        return [], []
    except RuntimeError as e:
        print(f"IS24 scraper failed: {e}")
        return [], []
    finally:
        if driver is not None:
            driver.quit()
            driver = None


def get_setup_url() -> str:
    url = _get_url_without_page(ReportType.HOUSE)
    return get_url_with_page(url, 1)


def _get_url_without_page(type: ReportType):
    return get_url_without_page(URL, ImmoPlatform.IMMOSCOUT, type)


def _get_results_of_type(type: ReportType) -> list[ImmoData]:
    listings = []
    url_without_page = _get_url_without_page(type)
    index = 1
    while True:
        url = get_url_with_page(url_without_page, index)
        print(url)
        soup = _get_soup(url, By.ID, "result-list-content")
        new_listings = soup.find_all("div", {"class": "listing-card"})
        listings += new_listings
        if len(new_listings) < 20:
            break
        index += 1
    return list(filter(lambda x: x is not None, map(lambda x: _get_immo_data(type, x), listings)))


def _get_soup(url, by, name):
    global driver
    try:
        if driver is None:
            driver = browser.get_driver(headless=False)
            browser.load_cookies(driver, "immoscout", BASE_URL)
        driver.get(url)
    except Exception:
        raise _BlockedException()
    if not browser.wait_for_element(driver, by, name, timeout=30):
        raise _BlockedException()
    return BeautifulSoup(driver.page_source, "html.parser")


def _get_immo_data(type, listing):
    infos = listing.find_all("dd", {"class": "font-bold"})
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
        link=BASE_URL + _get_href(listing),
        title=listing.find("h2", {"data-testid": "headline"}).text.strip(),
        price=price,
        living_area=living_area,
        land_area=land_area,
        type=type,
        distance=None,
        location=_get_location(listing),
    )


def _get_location(listing) -> str | None:
    elem = listing.find(attrs={"data-testid": "result-list-entry-address"})
    if elem:
        return elem.text.strip() or None
    return None


def _get_href(listing) -> Optional[str]:
    element = listing.find("a")
    if element:
        return element["href"]
