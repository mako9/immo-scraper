import requests
import re
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

    return list(map(lambda x: _get_immo_data(x), listings))


def _get_immo_data(listing):
    price = listing.find('div', {'data-test': 'price'}).text.strip()
    area = listing.find('div', {'data-test': 'area'}).text.strip()
    ratio = None

    if _is_not_empty(price) and _is_not_empty(area):
        ratio = _get_int_value_from_string(
            price) / _get_int_value_from_string(area)

    return ImmoData(
        link=listing.find('a')['href'],
        title=listing.find('h2').text.strip(),
        price=price,
        area=area,
        type=ReportType.HOUSE,
        ratio=ratio
    )


def _get_int_value_from_string(input_string):
    try:
        return int(re.sub('[^0-9]', '', input_string))
    except Exception as e:
        print(e)


def _is_not_empty(input_string):
    return input_string is not None and bool(input_string.strip())
