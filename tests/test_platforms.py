from bs4 import BeautifulSoup

from src.immo_data import ReportType
import src.immonet as immonet
import src.immoscout as immoscout
import src.immowelt as immowelt
import src.vr_immobilien as vr
import src.sparkasse as sparkasse
from src import kleinanzeigen
from bs4 import BeautifulSoup


def test_immonet_get_url_without_page_respects_env(monkeypatch):
    monkeypatch.setenv("LOCATION", "Berlin")
    monkeypatch.setenv("RADIUS", "30")
    monkeypatch.setenv("PRICE_UPPER_LIMIT", "300000")

    url = immonet._get_url_without_page(ReportType.HOUSE)
    assert "locationIds" in url
    assert "radius=30" in url
    assert "toprice=300000" in url
    assert "parentcat=2" in url


def test_immonet_get_immo_data_parses_expected_fields():
    html = """
    <sd-card>
      <a href="/immo/1"></a>
      <h3 class="tile-details__title">House Title</h3>
      <span class="is-bold ng-star-inserted">200.000 €</span>
      <span class="text-overflow ng-star-inserted">5 km</span>
      <span class="text-overflow ng-star-inserted">500 m²</span>
      <span class="ml-100 ng-star-inserted">120 m²</span>
    </sd-card>
    """

    listing = BeautifulSoup(html, "html.parser").find("sd-card")
    data = immonet._get_immo_data(ReportType.HOUSE, listing)

    assert data.title == "House Title"
    assert data.price == 200000.0
    assert data.distance == 5.0
    assert data.land_area == 500.0
    assert data.living_area == 120.0
    assert data.link == "/immo/1"


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
    data = immoscout._get_immo_data(ReportType.HOUSE, (listing_tag, None))

    assert data.title == "Scout Title"
    assert data.price == 100000.0
    assert data.living_area == 125.0
    assert data.land_area == 600.0
    assert data.link.endswith("/listing/1")


def test_immowelt_get_immo_data_parses_expected_fields():
    html = """
    <div>
      <a href="/immowelt/1"></a>
      <h2>ImmoWelt Listing</h2>
      <div data-test="price">150.000 €</div>
      <span>irrelevant</span>
      <span>2,5 km</span>
      <span>700 m²</span>
      <div data-test="area">130 m²</div>
    </div>
    """

    listing = BeautifulSoup(html, "html.parser").div
    data = immowelt._get_immo_data(ReportType.HOUSE, listing)

    assert data.title == "ImmoWelt Listing"
    assert data.price == 150000.0
    # ImmoData only extracts the integer portion of distance
    assert data.distance == 2.0
    assert data.land_area == 700.0
    assert data.living_area == 130.0
    assert data.link == "/immowelt/1"


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


# ----- Kleinanzeigen helpers/tests -----


def _make_list_page_html(has_next: bool):
    pagination_html = '<a class="pagination-next" href="#">next</a>' if has_next else ""
    return f"""
    <html>
      <body>
        <ul>
          <li class="ad-listitem fully-clickable-card">
            <article data-href="/detail/1">
              <h2 class="text-module-begin">My Title</h2>
              <div class="aditem-main--top--left">Ort (3km)</div>
            </article>
          </li>
        </ul>
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
