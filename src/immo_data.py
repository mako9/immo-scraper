from enum import Enum
from src.utils import get_int_value_from_string


class ReportType(Enum):
    HOUSE = 'HOUSE'
    LAND = 'LAND'

    def get_limits(self):
        if self == ReportType.HOUSE:
            return [0.3, 0.7]
        elif self == ReportType.LAND:
            return [0.3, 0.7]


class ImmoData:
    title: str
    price: int
    living_area: int
    land_area: int
    link: str
    type: ReportType
    ratio: float
    distance: int
    rating: float = 0.0

    def __init__(self, title, price, living_area, land_area, link, type, distance):
        self.title = title
        self.price = get_int_value_from_string(price)
        self.living_area = get_int_value_from_string(living_area)
        self.land_area = get_int_value_from_string(land_area)
        self.link = link
        self.type = type
        self.distance = get_int_value_from_string(distance)
        self.ratio = 0
        if self.price is not None and self.price > 0:
            if type == ReportType.HOUSE and (self.living_area is not None and self.living_area > 0):
                self.ratio = self.price / self.living_area
            elif self.land_area is not None and self.land_area > 0:
                self.ratio = self.price / self.land_area
