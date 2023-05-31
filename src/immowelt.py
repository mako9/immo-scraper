import requests
import os
from bs4 import BeautifulSoup
from src.immo_data import ImmoData, ReportType

URL = 'https://www.immowelt.de/liste/***/+++/kaufen?d=true&sd=DESC&sf=RELEVANCE&sp=$$$&r=§§§'


def get_immowelt_results():
    return _get_results_of_type(ReportType.HOUSE) + _get_results_of_type(ReportType.LAND)


def _get_url_without_page(type: ReportType):
    location = os.getenv('LOCATION')
    radius = os.getenv('RADIUS')
    url = URL.replace('***', location)
    url = url.replace('§§§', radius)
    replacement_string = 'haeuser'
    if (type == ReportType.LAND):
        replacement_string = 'grundstuecke'
    return url.replace('+++', replacement_string)


def _get_results_of_type(type: ReportType):
    # Set the search parameters
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    params = {'pma': f'{price_upper_limit}'}

    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)

    index = 1
    while True:
        url = url_without_page.replace('$$$', str(index))
        print(url)
        soup = _get_soup(url, params)
        new_listings = soup.find_all('div', {'class': 'EstateItem-1c115'})
        listings += new_listings
        if len(new_listings) < 20:
            break
        index += 1

    return list(map(lambda x: _get_immo_data(type, x), listings))


def _get_soup(url: str, params):
    # Send the request and get the HTML response
    response = requests.get(url, params=params)
    html = response.content

    # Parse the HTML response with BeautifulSoup
    return BeautifulSoup(html, 'html.parser')


def _get_immo_data(type: ReportType, listing):
    price = listing.find('div', {'data-test': 'price'}).text.strip()
    area = listing.find('div', {'data-test': 'area'}).text.strip()

    return ImmoData(
        link=listing.find('a')['href'],
        title=listing.find('h2').text.strip(),
        price=price,
        area=area,
        type=type
    )
