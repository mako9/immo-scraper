import re
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

BASE_URL = "https://www.kleinanzeigen.de"
URL = f"{BASE_URL}/+++/***/preis::###$$$/anzeige:angebote/c20^^^l4619r§§§"

executor_url: str = None
session_id: str = None
driver = None


def get_kleinanzeigen_results():
    house_listings = _get_results_of_type(ReportType.HOUSE)
    land_listings = _get_results_of_type(ReportType.LAND)

    driver.quit()

    return house_listings, land_listings


def _get_url_without_page(type: ReportType) -> str:
    url = get_url_without_page(URL, ImmoPlatform.KLEINANZEIGEN, type)
    if type == ReportType.LAND:
        return url.replace("^^^", "7")
    else:
        return url.replace("^^^", "8")


def _get_results_of_type(type: ReportType):
    # Find all the relevant listings
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

    filtered_listings = list(filter(lambda x: x is not None, listings))
    return list(map(lambda x: _get_immo_data(type, x), filtered_listings))


def _get_listing_soup(listing):
    href = _get_href(listing)
    if href is None:
        return None
    return _get_soup(f"{BASE_URL}{href}", "h1, section, main")


def _get_soup(url, css_selector):
    global driver  # Declare the variables as nonlocal
    # Send the request and get the HTML response
    if driver is None:
        service = Service()
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 60)  # Wait up to 60 seconds

    # Once we need to accept manually the Captcha. The browser session will then be reused.

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_selector)))

    html = driver.page_source

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    return soup


def _get_immo_data(type: ReportType, listing) -> Optional[ImmoData]:
    try:
        # Title — new design uses h3, old used h2.text-module-begin
        title_el = listing[0].find("h3") or listing[0].find("h2", {"class": "text-module-begin"})
        title = title_el.get_text(strip=True)

        # Location and distance
        loc_svg = listing[0].find("svg", attrs={"data-title": "locationOutline"})
        if loc_svg:
            location_text = loc_svg.parent.get_text(strip=True)
        else:
            location_text = listing[0].find("div", {"class": "aditem-main--top--left"}).get_text(strip=True)
        pattern = r"\(([^)]+)\)"
        distance_matches = re.findall(pattern, location_text)
        distance = distance_matches[0] if distance_matches else None
        location = re.sub(r"\s*\([^)]+\)\s*$", "", location_text).strip() or None

        # Price — new design has it in the card; fallback to old detail-page selector
        price_el = listing[0].find("p", class_=lambda c: c and "text-title3" in c)
        if price_el:
            price = price_el.get_text(strip=True)
        else:
            price = listing[1].find("h2", {"class": "boxedarticle--price"}).get_text(strip=True)

        # Living area — new design: "185 m² · 5 Zi." in the card
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

        # Land area — still from the detail page; try text-based search for new design
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
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            type=type,
            distance=distance,
            location=location,
        )
    except Exception:
        return None


def _get_url_with_page(url_without_page, index) -> str:
    if index == 1:
        return url_without_page.replace("$$$", "")
    else:
        updated_url = url_without_page.replace("$$$", "/seite:$$$")
        return get_url_with_page(updated_url, index)


def _get_href(listing) -> Optional[str]:
    # New design: data-href is directly on the article element
    href = listing.get("data-href")
    if href:
        return href
    # Old design: data-href was on a nested article
    article = listing.find("article")
    if article is None:
        return None
    try:
        return article["data-href"]
    except Exception:
        return None
