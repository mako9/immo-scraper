from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

import main
from src.immo_data import ReportType
import src.immoscout as immoscout
import src.immowelt as immowelt
import src.vr_immobilien as vr
import src.sparkasse as sparkasse
from src import kleinanzeigen
from bs4 import BeautifulSoup


def test_immoscout_get_immo_data_parses_expected_fields():
    listing_html = """
    <div>
      <a href="/listing/1"></a>
      <h2 data-testid="headline">Scout Title</h2>
      <dd class="font-bold">100.000 €</dd>
      <dd class="font-bold">125 m²</dd>
      <dd class="font-bold">unneeded</dd>
      <dd class="font-bold">600 m²</dd>
    </div>
    """

    listing_tag = BeautifulSoup(listing_html, "html.parser").div
    data = immoscout._get_immo_data(ReportType.HOUSE, listing_tag)

    assert data.title == "Scout Title"
    assert data.price == 100000.0
    assert data.living_area == 125.0
    assert data.land_area == 600.0
    assert data.link.endswith("/listing/1")
    assert data.location is None


def test_immoscout_get_immo_data_extracts_location():
    listing_html = """
    <div>
      <a href="/listing/1"></a>
      <h2 data-testid="headline">Scout Title</h2>
      <dd class="font-bold">100.000 €</dd>
      <dd class="font-bold">125 m²</dd>
      <dd class="font-bold">unneeded</dd>
      <dd class="font-bold">600 m²</dd>
      <span data-testid="result-list-entry-address">36043 Fulda</span>
    </div>
    """

    listing_tag = BeautifulSoup(listing_html, "html.parser").div
    data = immoscout._get_immo_data(ReportType.HOUSE, listing_tag)

    assert data.location == "36043 Fulda"


def test_immowelt_slugify():
    assert immowelt._slugify("Künzell") == "kuenzell"
    assert immowelt._slugify("München") == "muenchen"
    assert immowelt._slugify("Frankfurt am Main") == "frankfurt-am-main"
    assert immowelt._slugify("Köln") == "koeln"


def test_immowelt_resolve_location_passthrough(monkeypatch):
    monkeypatch.delenv("RADIUS", raising=False)
    assert immowelt._resolve_location("POCODE2604") == ("POCODE2604", None)
    assert immowelt._resolve_location("AD08DE2812") == ("AD08DE2812", None)
    assert immowelt._resolve_location("pocode2604") == ("pocode2604", None)


def test_immowelt_get_immo_data_parses_expected_fields():
    listing = {
        "hardFacts": {
            "title": "ImmoWelt Listing",
            "price": {"ariaLabel": "150000 €"},
            "facts": [
                {"type": "livingSpace", "splitValue": "130"},
                {"type": "plotSpace", "splitValue": "700"},
            ],
        },
        "url": "https://www.immowelt.de/expose/abc123",
    }
    data = immowelt._get_immo_data(ReportType.HOUSE, listing)

    assert data.title == "ImmoWelt Listing"
    assert data.price == 150000.0
    assert data.land_area == 700.0
    assert data.living_area == 130.0
    assert data.link == "https://www.immowelt.de/expose/abc123"
    assert data.distance is None
    assert data.location is None


def test_immowelt_get_immo_data_extracts_location_from_address():
    listing = {
        "hardFacts": {
            "title": "ImmoWelt Listing",
            "price": {"ariaLabel": "150000 €"},
            "facts": [],
        },
        "url": "https://www.immowelt.de/expose/abc123",
        "location": {"address": {"zipCode": "36043", "city": "Fulda"}},
    }
    data = immowelt._get_immo_data(ReportType.HOUSE, listing)

    assert data.location == "36043 Fulda"


def test_vr_immobilien_url_helpers_and_parsing():
    # URL helpers should replace object type and location placeholders
    assert "quick-objektarten=house" in vr._get_url_for_type(ReportType.HOUSE)
    assert "quick-objektarten=plot" in vr._get_url_for_type(ReportType.LAND)
    assert "Berlin" in vr._get_url_for_location("http://example.com/$$$", "Berlin")

    # Parsing
    html = """
    <div class="mw-object-col">
      <div class="mw-object-col-title">VR Title</div>
      <a class="mw-paginated-prop-anker-click" href="/vr/1"></a>
      <div class="mw-object-col-details-price-number">180.000 €</div>
      <div data-current-type="wohnflaeche">
        <div class="mw-object-col-details-info-col-number">140 m²</div>
      </div>
      <div data-current-type="grundstuecksfl">
        <div class="mw-object-col-details-info-col-number">530 m²</div>
      </div>
    </div>
    """
    listing = BeautifulSoup(html, "html.parser").find("div", {"class": "mw-object-col"})
    data = vr._get_immo_data(ReportType.HOUSE, listing)

    assert data.title == "VR Title"
    assert data.price == 180000.0
    assert data.living_area == 140.0
    assert data.land_area == 530.0
    assert data.link == "/vr/1"
    assert data.location is None


def test_vr_immobilien_get_immo_data_passes_city_as_location():
    html = """
    <div class="mw-object-col">
      <div class="mw-object-col-title">VR Title</div>
      <a class="mw-paginated-prop-anker-click" href="/vr/1"></a>
      <div class="mw-object-col-details-price-number">180.000 €</div>
    </div>
    """
    listing = BeautifulSoup(html, "html.parser").find("div", {"class": "mw-object-col"})
    data = vr._get_immo_data(ReportType.HOUSE, listing, city="Künzell")

    assert data.location == "Künzell"


def test_sparkasse_parse_number_and_api_mapping():
    assert sparkasse._parse_number("123.456 €") == "123.456"
    assert sparkasse._parse_number("") is None

    fake_estate = {
        "id": "XYZ",
        "headline": "Sparkasse Home",
        "main_facts": [
            {"label": "Kaufpreis", "value": "250.000 €"},
            {"label": "Wohnfl", "value": "110 m²"},
            {"label": "Grundst", "value": "620 m²"},
        ],
    }

    data = sparkasse._get_immo_data_from_api(ReportType.HOUSE, fake_estate)
    assert data.title == "Sparkasse Home"
    assert data.price == 250000.0
    assert data.living_area == 110.0
    assert data.land_area == 620.0
    assert "eid=XYZ" in data.link
    assert data.location is None


def test_sparkasse_extracts_location_from_geo_label():
    fake_estate = {
        "id": "ABC",
        "headline": "Sparkasse Home",
        "main_facts": [],
        "geo_label": "Fulda",
        "location": {"lat": 50.5433, "lon": 9.68345},
    }
    data = sparkasse._get_immo_data_from_api(ReportType.HOUSE, fake_estate)
    assert data.location == "Fulda"


def test_sparkasse_maps_current_api_response():
    current_api_estate = {
        "id": "FID-F12-388-804",
        "title": "Modernes Haus in Künzell",
        "subtitle": "Künzell",
        "priceData": {"value": "679.000 €"},
        "mainFacts": [
            {"name": "livingSpace", "value": "162 m²"},
            {"name": "propertySize", "value": "550 m²"},
        ],
    }

    data = sparkasse._get_immo_data_from_api(ReportType.HOUSE, current_api_estate)

    assert data.title == "Modernes Haus in Künzell"
    assert data.price == 679000.0
    assert data.living_area == 162.0
    assert data.land_area == 550.0
    assert data.location == "Künzell"
    assert "eid=FID-F12-388-804" in data.link


def test_sparkasse_uses_current_api_and_resolves_location(monkeypatch):
    class FakeResponse:
        status_code = 200
        text = '<div data-sip-api-proxy="/proxy"></div>'

        def __init__(self, payload=None):
            self._payload = payload

        def json(self):
            return self._payload

    requests = []

    def fake_post(_url, json, **_kwargs):
        requests.append(json)
        route = json["route"]
        if route.startswith("immobilien-api/locations?"):
            return FakeResponse([
                {"latitude": 50.53881, "longitude": 9.7062},
            ])
        if "estateTypeGroupingIds=396" in route:
            return FakeResponse({
                "totalItems": 1,
                "page": 1,
                "pageCount": 1,
                "estates": [{
                    "id": "house-1",
                    "title": "Haus",
                    "subtitle": "Künzell",
                    "priceData": {"value": "400.000 €"},
                    "mainFacts": [],
                }],
            })
        return FakeResponse({"totalItems": 0, "page": 1, "pageCount": 0, "estates": []})

    monkeypatch.setattr(sparkasse.requests, "get", lambda *_args, **_kwargs: FakeResponse())
    monkeypatch.setattr(sparkasse.requests, "post", fake_post)
    monkeypatch.setenv("LOCATION", "Künzell")
    monkeypatch.setenv("RADIUS", "10")
    monkeypatch.setenv("PRICE_UPPER_LIMIT", "1500000")

    houses, land = sparkasse.get_sparkasse_results()

    assert [listing.title for listing in houses] == ["Haus"]
    assert land == []
    location_query = parse_qs(urlparse(requests[0]["route"]).query)
    assert location_query == {"pattern": ["Künzell"], "limit": ["1"]}
    house_query = parse_qs(urlparse(requests[1]["route"]).query)
    assert house_query["latitude"] == ["50.53881"]
    assert house_query["longitude"] == ["9.7062"]
    assert house_query["radius"] == ["10"]
    assert house_query["maxPrice"] == ["1500000"]
    assert house_query["estateTypeGroupingIds"] == ["396"]
    assert house_query["offerType"] == ["2"]


def test_sparkasse_estates_route_omits_offerer_filter():
    route = sparkasse._build_estates_route(
        ReportType.HOUSE,
        page=1,
        size=10,
        coordinates=(50.53881, 9.7062),
        radius_km=10,
        max_price="1500000",
    )
    query = parse_qs(urlparse(route).query)
    # offererCategoryConfig is the bank's BLZ and restricted results to
    # Sparkasse-only offers; the site's own frontend omits it in searches.
    assert "offererCategoryConfig" not in query
    assert query["estateTypeGroupingIds"] == ["396"]
    assert query["offerType"] == ["2"]
    assert query["page"] == ["1"]
    assert query["pageSize"] == ["10"]


def test_sparkasse_post_api_request_retries_on_exception(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"estates": []}

    calls = []

    def fake_post(_url, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("transient failure")
        return FakeResponse()

    monkeypatch.setattr(sparkasse.requests, "post", fake_post)
    monkeypatch.setattr(sparkasse.time, "sleep", lambda _s: None)

    result = sparkasse._post_api_request("http://proxy", {"route": "r"})

    assert result == {"estates": []}
    assert len(calls) == 2


def test_sparkasse_post_api_request_returns_none_after_exhausting_retries(monkeypatch):
    calls = []

    def fake_post(_url, **_kwargs):
        calls.append(1)
        raise ConnectionError("persistent failure")

    monkeypatch.setattr(sparkasse.requests, "post", fake_post)
    monkeypatch.setattr(sparkasse.time, "sleep", lambda _s: None)

    assert sparkasse._post_api_request("http://proxy", {"route": "r"}) is None
    assert len(calls) == 8


# ----- Kleinanzeigen helpers/tests -----


def test_kleinanzeigen_get_setup_url_uses_first_house_search_page(monkeypatch):
    monkeypatch.setenv("ZIP_CODE", "36093")
    monkeypatch.setenv("RADIUS", "10")
    monkeypatch.setenv("PRICE_UPPER_LIMIT", "1500000")

    assert kleinanzeigen.get_setup_url() == (
        "https://www.kleinanzeigen.de/s-haus-kaufen/36093/"
        "preis::1500000/anzeige:angebote/c208l4619r10"
    )


def test_kleinanzeigen_setup_uses_search_url_generator():
    assert (
        main._SETUP_PLATFORMS["kleinanzeigen"]["setup_url_fn"]
        is kleinanzeigen.get_setup_url
    )


def _make_list_page_html(has_next: bool):
    pagination_html = '<a aria-label="Nächste" href="#">next</a>' if has_next else ""
    return f"""
    <html>
      <body>
        <article data-adid="123" data-href="/detail/1">
          <h3>My Title</h3>
          <div>
            <svg data-title="locationOutline"></svg>
            <span>Ort</span><span>(3 km)</span>
          </div>
          <p class="my-xsmall text-title3 font-strong text-secondary">123.456 €</p>
          <p class="font-strong text-onSurfaceSubdued">120 m² · 3 Zi.</p>
        </article>
        {pagination_html}
      </body>
    </html>
    """


def _make_detail_page_html():
    return """
    <html>
      <body>
        <h2 class="boxedarticle--price">123.456 €</h2>
        <ul>
          <li>Grundstücksfläche <span class="addetailslist--detail--value">750</span></li>
          <li>Wohnfläche <span class="addetailslist--detail--value">120</span></li>
        </ul>
      </body>
    </html>
    """


def test_kleinanzeigen_get_href_missing_article_returns_none():

    soup = BeautifulSoup("<li></li>", "html.parser")
    assert kleinanzeigen._get_href(soup) is None


def test_kleinanzeigen_was_blocked_set_on_exception(monkeypatch):
    monkeypatch.setattr(kleinanzeigen, "_get_results_of_type", lambda t: (_ for _ in ()).throw(kleinanzeigen._BlockedException()))
    kleinanzeigen.get_kleinanzeigen_results()
    assert kleinanzeigen.was_blocked is True


def test_kleinanzeigen_was_blocked_false_on_success(monkeypatch):
    monkeypatch.setattr(kleinanzeigen, "_get_results_of_type", lambda t: [])
    monkeypatch.setattr(kleinanzeigen, "driver", None)
    kleinanzeigen.get_kleinanzeigen_results()
    assert kleinanzeigen.was_blocked is False


def test_kleinanzeigen_get_immo_data_parses_expected_fields():
    listing_html = """
    <li>
      <article data-href="/detail/1">
        <h2 class="text-module-begin">Title Example</h2>
        <div class="aditem-main--top--left">Dorf (7km)</div>
      </article>
    </li>
    """
    listing_tag = BeautifulSoup(listing_html, "html.parser").li
    detail_soup = BeautifulSoup(_make_detail_page_html(), "html.parser")

    data = kleinanzeigen._get_immo_data(ReportType.HOUSE, (listing_tag, detail_soup))

    assert data.title == "Title Example"
    assert data.price == 123456.0
    assert data.living_area == 120.0
    assert data.land_area == 750.0
    assert data.distance == 7.0
    assert data.link.endswith("/detail/1")
    assert data.location == "Dorf"


def test_kleinanzeigen_get_immo_data_extracts_zip_and_city_as_location():
    listing_html = """
    <li>
      <article data-href="/detail/1">
        <h2 class="text-module-begin">Title Example</h2>
        <div class="aditem-main--top--left">36043 Fulda (5 km)</div>
      </article>
    </li>
    """
    listing_tag = BeautifulSoup(listing_html, "html.parser").li
    detail_soup = BeautifulSoup(_make_detail_page_html(), "html.parser")
    data = kleinanzeigen._get_immo_data(ReportType.HOUSE, (listing_tag, detail_soup))

    assert data.location == "36043 Fulda"


def test_kleinanzeigen_get_results_of_type_pagination(monkeypatch):
    # Patch the URL generation to keep things predictable
    monkeypatch.setattr(
        kleinanzeigen, "_get_url_without_page", lambda t: "http://example.com/page$$$"
    )

    # Create different list pages for page 1 and page 2
    page1 = BeautifulSoup(_make_list_page_html(has_next=True), "html.parser")
    page2 = BeautifulSoup(_make_list_page_html(has_next=False), "html.parser")
    detail = BeautifulSoup(_make_detail_page_html(), "html.parser")

    def fake_get_soup(url, class_name):
        # Detail pages are requested via the BASE_URL + data-href
        if "/detail/" in url:
            return detail

        # Page 1 is the base URL with no appended pagination marker.
        if url.endswith("/page") or url.endswith("page"):
            return page1

        # Page 2 uses the `seite:2` suffix (as generated by _get_url_with_page).
        if "seite:2" in url:
            return page2

        # Fallback to page1 to keep test stable.
        return page1

    monkeypatch.setattr(kleinanzeigen, "_get_soup", fake_get_soup)

    results = kleinanzeigen._get_results_of_type(ReportType.HOUSE)
    assert len(results) == 2
    assert all(r.link.endswith("/detail/1") for r in results)


def test_kleinanzeigen_keeps_prior_results_when_later_page_times_out(monkeypatch):
    page1 = BeautifulSoup(_make_list_page_html(has_next=True), "html.parser")
    detail = BeautifulSoup(_make_detail_page_html(), "html.parser")

    def fake_get_soup(url, _css_selector):
        if "/detail/" in url:
            return detail
        if "seite:2" in url:
            raise kleinanzeigen._BlockedException()
        return page1

    monkeypatch.setattr(kleinanzeigen, "was_blocked", False)
    monkeypatch.setattr(
        kleinanzeigen, "_get_url_without_page", lambda _type: "http://example.com/page$$$"
    )
    monkeypatch.setattr(kleinanzeigen, "_get_soup", fake_get_soup)

    results = kleinanzeigen._get_results_of_type(ReportType.HOUSE)

    assert [listing.title for listing in results] == ["My Title"]
    assert kleinanzeigen.was_blocked is False


def test_kleinanzeigen_keeps_list_results_when_a_detail_page_is_blocked(monkeypatch):
    page = BeautifulSoup(_make_list_page_html(has_next=False), "html.parser")
    monkeypatch.setattr(kleinanzeigen, "was_blocked", False)
    monkeypatch.setattr(kleinanzeigen, "_get_url_without_page", lambda _type: "http://example.com/page$$$")
    monkeypatch.setattr(kleinanzeigen, "_get_soup", lambda *_args: page)
    monkeypatch.setattr(
        kleinanzeigen,
        "_get_listing_soup",
        lambda _listing: (_ for _ in ()).throw(kleinanzeigen._BlockedException()),
    )

    results = kleinanzeigen._get_results_of_type(ReportType.HOUSE)

    assert [listing.title for listing in results] == ["My Title"]
    assert kleinanzeigen.was_blocked is True


def test_immoscout_was_blocked_set_on_exception(monkeypatch):
    monkeypatch.setattr(immoscout, "_get_results_of_type", lambda t: (_ for _ in ()).throw(immoscout._BlockedException()))
    immoscout.get_immoscout_results()
    assert immoscout.was_blocked is True


def test_immoscout_was_blocked_false_on_success(monkeypatch):
    monkeypatch.setattr(immoscout, "_get_results_of_type", lambda t: [])
    monkeypatch.setattr(immoscout, "driver", None)
    immoscout.get_immoscout_results()
    assert immoscout.was_blocked is False


def test_vr_immobilien_was_blocked_set_on_exception(monkeypatch):
    monkeypatch.setattr(vr, "_get_results_of_type", lambda t: (_ for _ in ()).throw(vr._BlockedException()))
    vr.get_vr_immobilien_results()
    assert vr.was_blocked is True


def test_vr_immobilien_was_blocked_false_on_success(monkeypatch):
    monkeypatch.setattr(vr, "_get_results_of_type", lambda t: [])
    monkeypatch.setattr(vr, "driver", None)
    vr.get_vr_immobilien_results()
    assert vr.was_blocked is False
