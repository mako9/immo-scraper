import os

from src.immo_data import ImmoData, ReportType

def calculate_rating(immo_data: list[ImmoData]):
    price_weight = float(os.getenv('PRICE_WEIGHT'))
    living_area_weight = float(os.getenv('LIVING_AREA_WEIGHT'))
    land_area_weight = float(os.getenv('LAND_AREA_WEIGHT'))
    distance_weight = float(os.getenv('DISTANCE_WEIGHT'))

    min_price, max_price = _get_min_max_values(list(map(lambda x: x.price, immo_data)))
    min_living_area, max_living_area = _get_min_max_values(list(map(lambda x: x.living_area, immo_data)))
    min_land_area, max_land_area = _get_min_max_values(list(map(lambda x: x.land_area, immo_data)))
    min_distance, max_distance = _get_min_max_values(list(map(lambda x: x.distance, immo_data)))

    for immo in immo_data:
        price_adjusted_value = _get_normalized_value(immo.price, min_price, max_price, inverted=True)
        living_area_adjusted_value = _get_normalized_value(immo.living_area, min_living_area, max_living_area)
        land_area_adjusted_value = _get_normalized_value(immo.land_area, min_land_area, max_land_area)
        distance_adjusted_value = _get_normalized_value(immo.distance, min_distance, max_distance, inverted=True)
        if (immo.type == ReportType.LAND):
            rating = price_weight * price_adjusted_value
            + (land_area_weight + living_area_weight) * land_area_adjusted_value
            + distance_weight * distance_adjusted_value
        else:
            rating = price_weight * price_adjusted_value
            + living_area_weight * living_area_adjusted_value
            + land_area_weight * land_area_adjusted_value
            + distance_weight * distance_adjusted_value


        # Scale the rating between 1 and 10
        min_rating = min(price_weight, living_area_weight, land_area_weight, distance_weight)
        max_rating = max(price_weight, living_area_weight, land_area_weight, distance_weight)
        scaled_rating = 1 + ((rating - min_rating) / (max_rating - min_rating)) * 9

        immo.rating = scaled_rating

def _get_min_max_values(values: list[int]):
    filtered_values = list(filter(lambda v: v is not None, values))
    if len(filtered_values) == 0:
        return None, None
    return min(filtered_values), max(filtered_values)

def _get_normalized_value(value, min_value, max_value, inverted=False):
    normalized_value = _normalize(value, min_value, max_value)
    if normalized_value is None:
        return 0
    if inverted:
        return 1 - normalized_value
    else:
        return normalized_value

def _normalize(value, min_value, max_value):
    if value is None or min_value is None or max_value is None or min_value == max_value:
        return None
    return (value - min_value) / (max_value - min_value)