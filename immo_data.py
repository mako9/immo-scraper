from enum import Enum


class ReportType(Enum):
    HOUSE = 'HOUSE'
    LAND = 'LAND'


class ImmoData:
    title: str
    price: int
    area: int
    link: str
    type: ReportType
    ratio: float

    def __init__(self, title, price, area, link, type, ratio):
        self.title = title
        self.price = price
        self.area = area
        self.link = link
        self.type = type
        self.ratio = ratio
