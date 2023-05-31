from enum import Enum
from src.utils import get_int_value_from_string


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
        self.title = title
        self.price = get_int_value_from_string(price)
        self.area = get_int_value_from_string(area)
        self.link = link
        self.type = type
        if self.area != 0:
            self.ratio = self.price / self.area
        else:
            self.ratio = -1
