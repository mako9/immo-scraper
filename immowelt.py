import requests
import os
from bs4 import BeautifulSoup
from immo_data import ImmoData, ReportType

URL = 'https://www.immowelt.de/liste/***/+++/kaufen?d=true&sd=DESC&sf=RELEVANCE&sp=1'


def get_results():
    return _get_results_of_type(ReportType.HOUSE) + _get_results_of_type(ReportType.LAND)


def _get_results_of_type(type: ReportType):
    location = os.getenv('LOCATION')
    url = URL.replace('***', location)
    replacement_string = 'haeuser'
    if (type == ReportType.LAND):
        replacement_string = 'grundstuecke'
    url = url.replace('+++', replacement_string)

    # Set the search parameters
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    params = {'pma': f'{price_upper_limit}'}

    # Send the request and get the HTML response
    response = requests.get(url, params=params)
    html = response.content

    # Parse the HTML response with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Find all the relevant listings
    listings = soup.find_all('div', {'class': 'EstateItem-1c115'})

    return list(map(lambda x: _get_immo_data(type, x), listings))


def _get_immo_data(type, listing):
    price = listing.find('div', {'data-test': 'price'}).text.strip()
    area = listing.find('div', {'data-test': 'area'}).text.strip()

    return ImmoData(
        link=listing.find('a')['href'],
        title=listing.find('h2').text.strip(),
        price=price,
        area=area,
        type=type
    )
