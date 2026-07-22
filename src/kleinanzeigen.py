import re
from typing import Optional
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
import src.browser as browser
from src.url import get_url_without_page, get_url_with_page
from src.immo_data import ImmoData, ReportType
from src.immo_platform import ImmoPlatform

BASE_URL = "https://www.kleinanzeigen.de"
URL = f"{BASE_URL}/+++/***/preis::###$$$/anzeige:angebote/c20^^^l4619r§§§"

driver = None


class _BlockedException(Exception):
    pass


def get_kleinanzeigen_results():
    global driver
    try:
        house_listings = _get_results_of_type(ReportType.HOUSE)
        land_listings = _get_results_of_type(ReportType.LAND)
        if driver is not None:
            browser.save_cookies(driver, "kleinanzeigen")
        return house_listings, land_listings
    except _BlockedException:
        print("Kleinanzeigen blocked — run 'python main.py --setup kleinanzeigen' to refresh session")
        return [], []
    finally:
        if driver is not None:
            driver.quit()
            driver = None


def _get_url_without_page(type: ReportType) -> str:
    url = get_url_without_page(URL, ImmoPlatform.KLEINANZEIGEN, type)
    if type == ReportType.LAND:
        return url.replace("^^^", "7")
    else:
        return url.replace("^^^", "8")


def _get_results_of_type(type: ReportType):
    listings = []
    url_without_page = _get_url_without_page(type)
    index = 1
    while True:
        url = _get_url_with_page(url_without_page, index)
        print(url)
        soup = _get_soup(url, "article[data-adid]")
        new_listings = soup.find_all("article", attrs={"data-adid": True})
        listings += list(map(lambda x: (x, _get_listing_soup(x)), new_listings))
        print(len(new_listings))
        if soup.find("a", {"aria-label": "Nächste"}) is None:
            break
        index += 1
    return list(map(lambda x: _get_immo_data(type, x), filter(lambda x: x is not None, listings)))


def _get_listing_soup(listing):
    href = _get_href(listing)
    if href is None:
        return None
    return _get_soup(f"{BASE_URL}{href}", "h1, section, main")


def _get_soup(url, css_selector):
    global driver
    if driver is None:
        driver = browser.get_driver(headless=True)
        browser.load_cookies(driver, "kleinanzeigen", BASE_URL)
    driver.get(url)
    if not browser.wait_for_element(driver, By.CSS_SELECTOR, css_selector, timeout=60):
        raise _BlockedException()
    return BeautifulSoup(driver.page_source, "html.parser")


def _get_immo_data(type: ReportType, listing) -> Optional[ImmoData]:
    try:
        title_el = listing[0].find("h3") or listing[0].find("h2", {"class": "text-module-begin"})
        title = title_el.get_text(strip=True)
        loc_svg = listing[0].find("svg", attrs={"data-title": "locationOutline"})
        if loc_svg:
            location_text = loc_svg.parent.get_text(strip=True)
        else:
            location_text = listing[0].find("div", {"class": "aditem-main--top--left"}).get_text(strip=True)
        distance_matches = re.findall(r"\(([^)]+)\)", location_text)
        distance = distance_matches[0] if distance_matches else None
        location = re.sub(r"\s*\([^)]+\)\s*$", "", location_text).strip() or None
        price_el = listing[0].find("p", class_=lambda c: c and "text-title3" in c)
        if price_el:
            price = price_el.get_text(strip=True)
        else:
            price = listing[1].find("h2", {"class": "boxedarticle--price"}).get_text(strip=True)
        living_area = None
        if type == ReportType.HOUSE:
            area_el = listing[0].find("p", class_=lambda c: c and "text-onSurfaceSubdued" in c and "font-strong" in c)
            if area_el:
                living_area = area_el.get_text(strip=True).split("·")[0].strip()
            elif listing[1]:
                try:
                    living_area = (
                        listing[1]
                        .find_all(lambda tag: tag.name == "li" and "Wohnfläche" in tag.text)[0]
                        .find("span", {"class": "addetailslist--detail--value"})
                        .get_text(strip=True)
                    )
                except Exception:
                    pass
        land_area = None
        if listing[1]:
            try:
                land_area = (
                    listing[1]
                    .find_all(lambda tag: tag.name == "li" and "Grundstücksfläche" in tag.text)[0]
                    .find("span", {"class": "addetailslist--detail--value"})
                    .get_text(strip=True)
                )
            except Exception:
                pass
            if not land_area:
                for text_node in listing[1].find_all(string=lambda t: "Grundstücksfläche" in str(t)):
                    container = text_node.find_parent(["li", "div", "tr", "dd"])
                    if container:
                        match = re.search(r"[\d.,]+\s*m²", container.get_text(strip=True).replace("Grundstücksfläche", ""))
                        if match:
                            land_area = match.group()
                            break
        href = _get_href(listing[0])
        return ImmoData(
            link=f"{BASE_URL}{href}",
            title=title, price=price,
            living_area=living_area, land_area=land_area,
            type=type, distance=distance, location=location,
        )
    except Exception:
        return None


def _get_url_with_page(url_without_page, index) -> str:
    if index == 1:
        return url_without_page.replace("$$$", "")
    updated_url = url_without_page.replace("$$$", "/seite:$$$")
    return get_url_with_page(updated_url, index)


def _get_href(listing) -> Optional[str]:
    href = listing.get("data-href")
    if href:
        return href
    article = listing.find("article")
    if article is None:
        return None
    try:
        return article["data-href"]
    except Exception:
        return None
