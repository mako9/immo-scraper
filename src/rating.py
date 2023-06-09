import os

from src.immo_data import ImmoData, ReportType

def calculate_rating(immo_data: list[ImmoData]):
    price_weight = float(os.getenv('PRICE_WEIGHT'))
    living_area_weight = float(os.getenv('LIVING_AREA_WEIGHT'))
    land_area_weight = float(os.getenv('LAND_AREA_WEIGHT'))
    distance_weight = float(os.getenv('DISTANCE_WEIGHT'))

    (min_price, max_price) = _get_min_max_values(list(map(lambda x: x.price, immo_data)))
    (min_living_area, max_living_area) = _get_min_max_values(list(map(lambda x: x.living_area, immo_data)))
    (min_land_area, max_land_area) = _get_min_max_values(list(map(lambda x: x.land_area, immo_data)))
    (min_distance, max_distance) = _get_min_max_values(list(map(lambda x: x.distance, immo_data)))

    for immo in immo_data:
        price_adjusted_value = (1 - _normalize(immo.price, min_price, max_price))
        living_area_adjusted_value = _normalize(immo.living_area, min_living_area, max_living_area)
        land_area_adjusted_value = _normalize(immo.land_area, min_land_area, max_land_area)
        distance_adjusted_value = (1 - _normalize(immo.distance, min_distance, max_distance))
        rating = price_weight * price_adjusted_value
        + living_area_weight * living_area_adjusted_value
        + land_area_weight * land_area_adjusted_value
        + distance_weight * distance_adjusted_value

        if (immo.type == ReportType.LAND):
            rating = price_weight * price_adjusted_value
            + (land_area_weight + living_area_weight) * land_area_adjusted_value
            + distance_weight * distance_adjusted_value

        immo.rating = rating * 10

def _get_min_max_values(values: list[int]):
    filtered_values = list(filter(lambda v: v is not None, values))
    if len(filtered_values) == 0:
        return 1, 1
    return min(filtered_values), max(filtered_values)

def _normalize(value, min_value, max_value):
    if value is None:
        return 0
    return (value - min_value) / (max_value - min_value)