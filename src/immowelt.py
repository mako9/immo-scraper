import requests
import os
from bs4 import BeautifulSoup

from src.url import get_url_without_page, get_url_with_page
from src.immo_data import ImmoData, ReportType
from src.immo_platform import ImmoPlatform

URL = 'https://www.immowelt.de/liste/***/+++/kaufen?d=true&sd=DESC&sf=RELEVANCE&sp=$$$&r=§§§'


def get_immowelt_results():
    return _get_results_of_type(ReportType.HOUSE), _get_results_of_type(ReportType.LAND)


def _get_url_without_page(type: ReportType):
    return get_url_without_page(URL, ImmoPlatform.IMMOWELT, type)


def _get_results_of_type(type: ReportType):
    # Set the search parameters
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    params = {'pma': f'{price_upper_limit}'}

    # Find all the relevant listings
    listings = []
    url_without_page = _get_url_without_page(type)

    index = 1
    while True:
        url = get_url_with_page(url_without_page, index)
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
    elements = listing.findAll('span')
    distance = elements[1].text.strip().replace('.', ',')
    living_area = None
    land_area = None
    if len(elements) > 2:
        land_area = elements[2].text.strip().replace('.', ',')
    if type == ReportType.HOUSE:
        living_area = listing.find('div', {'data-test': 'area'}).text.strip().replace('.', ',')

    return ImmoData(
        link=listing.find('a')['href'],
        title=listing.find('h2').text.strip(),
        price=price,
        living_area=living_area,
        land_area=land_area,
        type=type,
        distance=distance
    )
