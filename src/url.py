import os

from src.immo_platform import ImmoPlatform
from src.immo_data import ReportType

URL = 'https://www.immowelt.de/liste/***/+++/kaufen?d=true&sd=DESC&sf=RELEVANCE&sp=$$$&r=§§§'
URL = 'https://www.immobilienscout24.de/Suche/radius/+++?centerofsearchaddress=Fulda%20(Kreis);;;1276007005017;;$$$&geocoordinates=50.54398;9.7184;§§§.0&enteredFrom=one_step_search&pagenumber=***&price=-###'
URL = 'https://www.immonet.de/immobiliensuche/beta?objecttype=1&locationIds=134762&radius=§§§&parentcat=+++&marketingtype=1&page=$$$'

def get_url_without_page(url: str, platform: ImmoPlatform, type: ReportType):
    location = os.getenv('LOCATION')
    radius = os.getenv('RADIUS')
    price_upper_limit = os.getenv('PRICE_UPPER_LIMIT')
    url = url.replace('***', location)
    url = url.replace('§§§', radius)
    url = url.replace('###', price_upper_limit)
    replacement_string = platform.get_url_replacement_string(type)
    return url.replace('+++', replacement_string)

def get_url_with_page(url: str, pageIndex: int):
    return url.replace('$$$', str(pageIndex))