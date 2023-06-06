import os
from bs4 import BeautifulSoup
from src.immo_data import ImmoData, ReportType
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = 'https://www.immobilienscout24.de/Suche/radius/+++?centerofsearchaddress=Fulda%20(Kreis);;;1276007005017;;$$$&geocoordinates=50.54398;9.7184;§§§.0&enteredFrom=one_step_search&pagenumber=***&price=-###'

executor_url: str = None
session_id: str = None
driver = None

def get_immoscout_results():
    house_listings = _get_results_of_type(ReportType.HOUSE)
    land_listings = _get_results_of_type(ReportType.LAND)

    driver.quit()

    return house_listings, land_listings


def _get_url_without_page(type: ReportType):
    location = os.getenv('LOCATION')
    radius = os.getenv('RADIUS')
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    url = URL.replace('$$$', location)
    url = url.replace('§§§', radius)
    url = url.replace('###', price_upper_limit)
    replacement_string = 'grundstueck-kaufen'
    if (type == ReportType.HOUSE):
        replacement_string = 'haus-kaufen'
    return url.replace('+++', replacement_string)


def _get_results_of_type(type: ReportType):
    # Set the search parameters

    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)

    index = 1
    while True:
        url = url_without_page.replace('***', str(index))
        print(url)
        soup = _get_soup(url)
        new_listings = soup.find_all('li', {'class': 'result-list__listing'})
        listings += new_listings
        if len(new_listings) < 20:
            break
        index += 1

    return list(map(lambda x: _get_immo_data(type, x), listings))


def _get_soup(url):
    global driver  # Declare the variables as nonlocal
    # Send the request and get the HTML response
    options = Options()
    #options.add_argument("--headless")  # Run Chrome in headless mode
    service = Service(ChromeDriverManager().install())
    if driver is None:
        driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    wait = WebDriverWait(driver, 60)  # Wait up to 60 seconds

    # Once we need to accept manually the Captcha. The browser session will then be reused.

    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'result-list-content')))

    html = driver.page_source

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    return soup


def _get_immo_data(type, listing):
    infos = listing.findAll(
        'dd', {'class': 'font-highlight font-tabular'})
    price = infos[0].text.strip()
    living_area = None
    if type == ReportType.HOUSE:
        living_area = infos[1].text.strip()
        land_area = infos[3].text.strip()
    else:
        land_area = infos[1].text.strip()

    return ImmoData(
        link='https://www.immobilienscout24.de' +
        listing.find('a', {'class': 'result-list-entry__brand-title-container'})['href'],
        title=listing.find('h2').text.strip(),
        price=price,
        living_area=living_area,
        land_area=land_area,
        type=type,
        distance=None
    )
