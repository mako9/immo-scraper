import pytest

from src.utils import get_int_value_from_string


@pytest.mark.parametrize(
    "input_value,expected",
    [
        (None, None),
        ("1.234,56 €", 1234.0),
        ("Preis: 999", 999.0),
        ("no digits here", None),
    ],
)
def test_get_int_value_from_string_basic(input_value, expected):
    assert get_int_value_from_string(input_value) == expected


def test_get_int_value_from_string_non_string_returns_none():
    assert get_int_value_from_string(123) is None
