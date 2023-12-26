import os

from src.immo_platform import ImmoPlatform
from src.immo_data import ReportType

def get_url_without_page(url: str, platform: ImmoPlatform, type: ReportType):
    location = platform.get_location()
    radius = os.getenv('RADIUS')
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    url = url.replace('***', location)
    url = url.replace('§§§', radius)
    url = url.replace('###', price_upper_limit)
    replacement_string = platform.get_url_replacement_string(type)
    return url.replace('+++', replacement_string)

def get_url_with_page(url: str, pageIndex: int):
    return url.replace('$$$', str(pageIndex))