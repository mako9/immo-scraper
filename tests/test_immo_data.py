import pytest

from src.immo_data import ImmoData, ReportType


def test_immo_data_ratio_for_house_uses_living_area():
    data = ImmoData(
        title="Test",
        price="200000",
        living_area="100",
        land_area="500",
        link="http://example.com/1",
        type=ReportType.HOUSE,
        distance="10",
    )

    assert data.ratio == 2000.0


def test_immo_data_ratio_for_land_uses_land_area():
    data = ImmoData(
        title="Test",
        price="200000",
        living_area="100",
        land_area="500",
        link="http://example.com/1",
        type=ReportType.LAND,
        distance="10",
    )

    assert data.ratio == 400.0


def test_immo_data_equality_and_hash_use_link():
    a = ImmoData(
        title="A",
        price="100",
        living_area="50",
        land_area="100",
        link="http://example.com/1",
        type=ReportType.HOUSE,
        distance="5",
    )
    b = ImmoData(
        title="B",
        price="200",
        living_area="150",
        land_area="50",
        link="http://example.com/1",
        type=ReportType.LAND,
        distance="10",
    )

    assert a == b
    assert hash(a) == hash(b)


def test_immo_data_equality_fallback_without_link():
    a = ImmoData(
        title="A",
        price="100",
        living_area="50",
        land_area="100",
        link=None,
        type=ReportType.HOUSE,
        distance="5",
    )
    b = ImmoData(
        title="A",
        price="100",
        living_area="200",
        land_area="100",
        link=None,
        type=ReportType.HOUSE,
        distance="5",
    )

    assert a == b
    assert hash(a) == hash(b)
