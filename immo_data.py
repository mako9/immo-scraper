import re
from enum import Enum


class ReportType(Enum):
    HOUSE = 'HOUSE'
    LAND = 'LAND'

    def get_limits(self):
        if self == ReportType.HOUSE:
            return [2000, 4000]
        elif self == ReportType.LAND:
            return [500, 1000]


class ImmoData:
    title: str
    price: int
    area: int
    link: str
    type: ReportType
    ratio: float

    def __init__(self, title, price, area, link, type):
        ratio = None

        if _is_not_empty(price) and _is_not_empty(area):
            ratio = _get_int_value_from_string(
                price.replace('.', '')) / _get_int_value_from_string(area)

        self.title = title
        self.price = price
        self.area = area
        self.link = link
        self.type = type
        self.ratio = ratio


def _get_int_value_from_string(input_string):
    try:
        match = re.search(r'\d+(\.\d+)?', input_string)
        if match:
            return float(match.group())
    except Exception as e:
        print(e)


def _is_not_empty(input_string):
    return input_string is not None and bool(input_string.strip())
