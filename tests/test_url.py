from src.immo_data import ReportType
from src.immo_platform import ImmoPlatform
from src.url import get_url_without_page, get_url_with_page


def test_get_url_with_page_replaces_placeholder():
    assert get_url_with_page("/foo/$$$/bar", 1) == "/foo/1/bar"
    assert get_url_with_page("/foo/$$$/bar", 42) == "/foo/42/bar"


def test_get_url_without_page_replaces_all_placeholders(monkeypatch):
    monkeypatch.setenv("LOCATION", "Musterstadt")
    monkeypatch.setenv("ZIP_CODE", "12345")
    monkeypatch.setenv("RADIUS", "10")
    monkeypatch.setenv("PRICE_UPPER_LIMIT", "500000")

    template = "https://example.com/+++/***/preis::###$$$/anzeige/§§§"

    url_house = get_url_without_page(
        template, ImmoPlatform.KLEINANZEIGEN, ReportType.HOUSE
    )
    assert "s-haus-kaufen" in url_house
    assert "12345" in url_house
    assert "10" in url_house
    assert "500000" in url_house

    url_land = get_url_without_page(
        template, ImmoPlatform.KLEINANZEIGEN, ReportType.LAND
    )
    assert "s-grundstuecke-garten" in url_land
    assert "12345" in url_land
    assert "10" in url_land
    assert "500000" in url_land


def test_get_url_without_page_uses_location_for_platforms(monkeypatch):
    # Ensure the LOCATION env var is used for platforms other than KLEINANZEIGEN
    monkeypatch.setenv("LOCATION", "Hamburg")
    monkeypatch.setenv("RADIUS", "5")
    monkeypatch.setenv("PRICE_UPPER_LIMIT", "100000")

    template = "https://example.com/+++/***/preis::###$$$/anzeige/§§§"
    url = get_url_without_page(template, ImmoPlatform.IMMONET, ReportType.HOUSE)
    assert "Hamburg" in url
