import requests
import os
from bs4 import BeautifulSoup
from src.immo_data import ImmoData, ReportType

URL = 'https://www.immobilienscout24.de/Suche/radius/+++?centerofsearchaddress=Fulda%20(Kreis);;;1276007005017;;$$$&geocoordinates=50.54398;9.7184;§§§.0&enteredFrom=one_step_search'


def get_immoscout_results():
    return _get_results_of_type(ReportType.HOUSE) + _get_results_of_type(ReportType.LAND)


def _get_url_without_page():
    location = os.getenv('LOCATION')
    radius = os.getenv('RADIUS')
    url = URL.replace('$$$', location)
    url = url.replace('§§§', radius)
    replacement_string = 'grundstueck-kaufen'
    if (type == ReportType.HOUSE):
        replacement_string = 'haus-kaufen'
    return url.replace('+++', replacement_string)


def _get_results_of_type(type: ReportType):
    # Set the search parameters
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    params = {'price': f'<= {price_upper_limit}', 'sorting': '2'}

    # Find all the relevant listings
    listings = []

    index = 1
    while True:
        url = _get_url_without_page()
        print(url)
        soup = _get_soup(url, params)
        print(soup)
        new_listings = soup.find_all('li', {'class': 'result-list__listing'})
        listings += new_listings
        index += 1
        if len(new_listings) < 20:
            break

    return list(map(lambda x: _get_immo_data(type, x), listings))


def _get_soup(url, params):
    # Send the request and get the HTML response
    response = requests.get(url, params=params)
    html = response.content

    # Parse the HTML response with BeautifulSoup
    return BeautifulSoup(html, 'html.parser')


def _get_immo_data(type, listing):
    price = listing.find(
        'dd', {'grid-item result-list-entry__primary-criterion'}).find('dd').text.strip()
    area = listing.find(
        'dd', {'class': 'is24qa-wohnflaeche-ca grid-item three-fifths'}).text.strip()

    return ImmoData(
        link='https://www.immobilienscout24.de/expose/' +
        listing.find('a')['href'],
        title=listing.find(
            'h5', {'class': 'result-list-entry__brand-title'}).text.strip(),
        price=price,
        area=area,
        type=type
    )
