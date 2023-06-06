import os

from src.immo_data import ImmoData

def calculate_rating(immo_data: list[ImmoData]):
    price_weight = float(os.getenv('PRICE_WEIGHT'))
    living_area_weight = float(os.getenv('LIVING_AREA_WEIGHT'))
    land_area_weight = float(os.getenv('LAND_AREA_WEIGHT'))
    distance_weight = float(os.getenv('DISTANCE_WEIGHT'))

    (min_price, max_price) = _get_min_max_values(list(map(lambda x: x.price, immo_data)))
    (min_living_area, max_living_area) = _get_min_max_values(list(map(lambda x: x.price, immo_data)))
    (min_land_area, max_land_area) = _get_min_max_values(list(map(lambda x: x.price, immo_data)))
    (min_distance, max_distance) = _get_min_max_values(list(map(lambda x: x.price, immo_data)))

    for immo in immo_data:
        immo.rating = price_weight * _normalize(immo.price, min_price, max_price)
        + living_area_weight * _normalize(immo.living_area, min_living_area, max_living_area)
        + land_area_weight * _normalize(immo.land_area, min_land_area, max_land_area)
        + distance_weight * _normalize(immo.distance, min_distance, max_distance)

def _get_min_max_values(values: list[int]):
    return (min(values), max(values))

def _normalize(value, min_value, max_value):
    if value is None:
        return -1
    return (value - min_value) / (max_value - min_value)