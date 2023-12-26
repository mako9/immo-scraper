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

BASE_URL = 'https://www.kleinanzeigen.de'
URL = f'{BASE_URL}/+++/***/preis::###$$$/c20^^^l4619r§§§'

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
        return url.replace('^^^', '7')
    else:
        return url.replace('^^^', '8')


def _get_results_of_type(type: ReportType):
    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)

    index = 1
    while True:
        url = _get_url_with_page(url_without_page, index)
        print(url)
        soup = _get_soup(url, 'site-base--content')
        new_listings = soup.find_all('li', {'class': 'ad-listitem'})
        listings += list(map(lambda x: (x, _get_listing_soup(x)), new_listings))
        if len(new_listings) < 25:
            break
        index += 1

    filtered_listings = list(filter(lambda x: x is not None, listings))
    return list(map(lambda x: _get_immo_data(type, x), filtered_listings))


def _get_listing_soup(listing):
    href = _get_href(listing)
    if href is None:
        return None
    return _get_soup(f'{BASE_URL}{href}', 'site-base--content')


def _get_soup(url, class_name):
    global driver  # Declare the variables as nonlocal
    # Send the request and get the HTML response
    if driver is None:
        service = Service()
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 60)  # Wait up to 60 seconds

    # Once we need to accept manually the Captcha. The browser session will then be reused.

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))

    html = driver.page_source

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    return soup


def _get_immo_data(type: ReportType, listing) -> ImmoData:
    try:
        title = listing[0].find('h2', {'class': 'text-module-begin'}).text.strip()
        pattern = r'\(([^)]+)\)'
        location_text = listing[0].find('div', {'class': 'aditem-main--top--left'}).text.strip()
        distance = re.findall(pattern, location_text)[0]
        price = listing[1].find('h2', {'class': 'boxedarticle--price'}).text.strip()
        living_area = None
        land_area = listing[1].find_all(lambda tag: tag.name == "li" and 'Grundstücksfläche' in tag.text)[0].find('span', {'class': 'addetailslist--detail--value'}).text.strip()
        if type == ReportType.HOUSE:
            living_area = listing[1].find_all(lambda tag: tag.name == "li" and 'Wohnfläche' in tag.text)[0].find('span', {'class': 'addetailslist--detail--value'}).text.strip()
        href = _get_href(listing[0])
        return ImmoData(
            link=f'{BASE_URL}{href}',
            title=title,
            price=price,
            living_area=living_area,
            land_area=land_area,
            type=type,
            distance=distance
        )
    except:
        return None


def _get_url_with_page(url_without_page, index) -> str:
    if index == 1:
        return url_without_page.replace('$$$', '')
    else:
        updated_url = url_without_page.replace('$$$', '/seite:$$$')
        return get_url_with_page(updated_url, index)
   
    
def _get_href(listing) -> Optional[str]:
    article = listing.find('article')
    if article is None:
        return None
    try:
        return article['data-href']
    except:
        return None
