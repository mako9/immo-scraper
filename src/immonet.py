import os
import time
from bs4 import BeautifulSoup
from src.immo_data import ImmoData, ReportType
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.utils import get_int_value_from_string

URL = 'https://www.immonet.de/immobiliensuche/beta?objecttype=1&locationIds=134762&radius=§§§&parentcat=+++&marketingtype=1&page=$$$'

def get_immonet_results():
    return _get_results_of_type(ReportType.HOUSE) + _get_results_of_type(ReportType.LAND)


def _get_url_without_page(type: ReportType):
    location = os.getenv('LOCATION')
    radius = os.getenv('RADIUS')
    url = URL.replace('***', location)
    url = url.replace('§§§', radius)
    replacement_string = '3'
    if (type == ReportType.HOUSE):
        replacement_string = '2'
    return url.replace('+++', replacement_string)


def _get_results_of_type(type: ReportType):
    # Set the search parameters
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    params = {'price': f'<= {price_upper_limit}'}

    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)
    soup = _get_soup(url_without_page, params)
    total_count = get_int_value_from_string(soup.find('h1', {'class': 'is-bold'}).text.strip())

    index = 1
    while True:
        url = url_without_page.replace('$$$', str(index))
        print(url)
        soup = _get_soup(url, params)
        new_listings = soup.find_all('sd-card')
        listings += new_listings
        if len(listings) >= total_count or len(new_listings) < 20:
            break
        index += 1

    return list(map(lambda x: _get_immo_data(type, x), listings))


def _get_soup(url, params):
    # Send the request and get the HTML response
    options = Options()
    options.add_argument("--headless")  # Run Chrome in headless mode
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds

    wait.until(EC.presence_of_element_located((By.TAG_NAME, 'sd-card')))
    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

    html = driver.page_source

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    driver.quit()

    return soup


def _get_immo_data(type, listing):
    link = listing.find('a').attrs['href']
    title = listing.find(
        'h3', {'class': 'tile-details__title'}).text.strip()
    price = listing.find(
        'span', {'class': 'is-bold ng-star-inserted'}).text.strip()
    areaElement = listing.find(
        'span', {'class': 'ml-100 ng-star-inserted'})
    area = ""
    if areaElement is not None:
        area = areaElement.text.strip()

    return ImmoData(
        link=link,
        title=title,
        price=price,
        area=area,
        type=type
    )
