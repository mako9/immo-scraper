import openpyxl

import src.xls as xls
from src.immo_data import ImmoData, ReportType


def _make_listing(title, link="", price="500000", living_area="100",
                  land_area=None, type=ReportType.HOUSE):
    return ImmoData(title, price, living_area, land_area, link, type, distance="5")


def _seen_by_title(path, sheet="Houses"):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    markers = {row[1]: row[0] for row in ws.iter_rows(min_row=2, max_col=10, values_only=True) if row[1]}
    wb.close()
    return markers


def test_header_seen_before_in_column_a_and_no_type_column(tmp_path, monkeypatch):
    path = tmp_path / "immo-results.xlsx"
    monkeypatch.setattr(xls, "RESULT_FILE", str(path))
    xls.write_listings([_make_listing("House A", "https://a.com/1")], [])
    wb = openpyxl.load_workbook(path)
    for ws in wb.worksheets:
        assert ws["A1"].value == "Seen Before"
        assert ws["K1"].value is None
    wb.close()


def test_first_run_marks_all_entries_as_not_seen(tmp_path, monkeypatch):
    path = tmp_path / "immo-results.xlsx"
    monkeypatch.setattr(xls, "RESULT_FILE", str(path))
    a = _make_listing("House A", "https://a.com/1")
    b = _make_listing("House B", "https://b.com/2")
    xls.write_listings([a, b], [])
    markers = _seen_by_title(str(path))
    assert markers == {"House A": "No", "House B": "No"}


def test_second_run_marks_previous_entries_as_seen(tmp_path, monkeypatch):
    path = tmp_path / "immo-results.xlsx"
    monkeypatch.setattr(xls, "RESULT_FILE", str(path))
    a = _make_listing("House A", "https://a.com/1")
    b = _make_listing("House B", "https://b.com/2")
    xls.write_listings([a, b], [])

    c = _make_listing("House C", "https://c.com/3")
    xls.write_listings([a, c], [])

    markers = _seen_by_title(str(path))
    assert markers == {"House A": "Yes", "House C": "No"}


def test_land_sheet_is_marked_against_previous_results(tmp_path, monkeypatch):
    path = tmp_path / "immo-results.xlsx"
    monkeypatch.setattr(xls, "RESULT_FILE", str(path))
    land = _make_listing("Land L", "https://l.com/1", price="100000",
                         living_area=None, land_area="500", type=ReportType.LAND)
    xls.write_listings([], [land])
    assert _seen_by_title(str(path), sheet="Land") == {"Land L": "No"}

    xls.write_listings([], [land])
    assert _seen_by_title(str(path), sheet="Land") == {"Land L": "Yes"}


def test_entries_without_link_match_by_title_price_and_land_area(tmp_path, monkeypatch):
    path = tmp_path / "immo-results.xlsx"
    monkeypatch.setattr(xls, "RESULT_FILE", str(path))
    a = _make_listing("No Link House", "", price="300000",
                      living_area=None, land_area="500")
    xls.write_listings([a], [])

    same = _make_listing("No Link House", "", price="300000",
                         living_area=None, land_area="500")
    changed = _make_listing("No Link House", "", price="310000",
                            living_area=None, land_area="500")
    xls.write_listings([same, changed], [])

    # Both rows share the same title, so compare on links would fail; check by row order
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Houses"]
    rows = list(ws.iter_rows(min_row=2, max_col=10, values_only=True))
    wb.close()
    markers = sorted(row[0] for row in rows)
    assert markers == ["No", "Yes"]
