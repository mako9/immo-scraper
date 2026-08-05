import datetime
import openpyxl
import pytest
from unittest.mock import patch, MagicMock

import src.immoscout as immoscout
import src.kleinanzeigen as kleinanzeigen
import src.vr_immobilien as vr_immobilien
import run_daily


def _make_xlsx(tmp_path, entries):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Houses"
    wb.create_sheet("Land")
    for i, (title, link) in enumerate(entries, start=2):
        ws.cell(row=i, column=2, value=title)
        ws.cell(row=i, column=10, value=link)
    path = tmp_path / "immo-results.xlsx"
    wb.save(str(path))
    return str(path)


# --- _read_top_n ---

def test_read_top_n_returns_empty_when_file_missing(tmp_path):
    result = run_daily._read_top_n(str(tmp_path / "missing.xlsx"), 30)
    assert result == []


def test_read_top_n_returns_titles_and_links(tmp_path):
    path = _make_xlsx(tmp_path, [("House A", "https://a.com"), ("House B", "https://b.com")])
    result = run_daily._read_top_n(path, 30)
    assert ("House A", "https://a.com") in result
    assert ("House B", "https://b.com") in result


def test_read_top_n_respects_limit(tmp_path):
    entries = [(f"House {i}", f"https://example.com/{i}") for i in range(5)]
    path = _make_xlsx(tmp_path, entries)
    result = run_daily._read_top_n(path, 3)
    assert len(result) == 3


def test_read_top_n_skips_rows_without_link(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Houses"
    wb.create_sheet("Land")
    ws.cell(row=2, column=2, value="No Link House")
    ws.cell(row=3, column=2, value="With Link House")
    ws.cell(row=3, column=10, value="https://example.com/1")
    path = tmp_path / "immo-results.xlsx"
    wb.save(str(path))
    result = run_daily._read_top_n(str(path), 30)
    assert len(result) == 1
    assert result[0][1] == "https://example.com/1"


# --- _already_ran_today / _mark_ran_today ---

def test_already_ran_today_false_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(tmp_path / ".last_run_date"))
    assert run_daily._already_ran_today() is False


def test_already_ran_today_true_when_todays_date(tmp_path, monkeypatch):
    last_run = tmp_path / ".last_run_date"
    last_run.write_text(str(datetime.date.today()))
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(last_run))
    assert run_daily._already_ran_today() is True


def test_already_ran_today_false_when_old_date(tmp_path, monkeypatch):
    last_run = tmp_path / ".last_run_date"
    last_run.write_text(str(datetime.date.today() - datetime.timedelta(days=1)))
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(last_run))
    assert run_daily._already_ran_today() is False


def test_mark_ran_today_writes_todays_date(tmp_path, monkeypatch):
    last_run = tmp_path / ".last_run_date"
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(last_run))
    run_daily._mark_ran_today()
    assert last_run.read_text().strip() == str(datetime.date.today())


# --- main() ---

def test_main_skips_when_already_ran_today(tmp_path, monkeypatch):
    last_run = tmp_path / ".last_run_date"
    last_run.write_text(str(datetime.date.today()))
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(last_run))
    with patch("run_daily.load_and_store_data") as mock_scrape:
        run_daily.main()
    mock_scrape.assert_not_called()


def test_main_sends_email_on_new_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(tmp_path / ".last_run_date"))
    monkeypatch.setenv("TOP_N", "30")

    old_xlsx = _make_xlsx(tmp_path, [("Old House", "https://old.com/1")])
    new_entries = [("Old House", "https://old.com/1"), ("New House", "https://new.com/2")]

    call_count = 0

    def fake_read_top_n(path, n):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [("Old House", "https://old.com/1")]
        return new_entries

    monkeypatch.setattr(run_daily, "_read_top_n", fake_read_top_n)

    with patch("run_daily.load_and_store_data"), \
         patch("run_daily.send_new_listings_email") as mock_notify:
        run_daily.main()

    mock_notify.assert_called_once()
    notified_entries = mock_notify.call_args[0][0]
    assert ("New House", "https://new.com/2") in notified_entries
    assert ("Old House", "https://old.com/1") not in notified_entries


def test_main_no_email_when_no_new_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(tmp_path / ".last_run_date"))
    monkeypatch.setenv("TOP_N", "30")

    same_entries = [("House A", "https://example.com/1")]

    monkeypatch.setattr(run_daily, "_read_top_n", lambda path, n: same_entries)

    with patch("run_daily.load_and_store_data"), \
         patch("run_daily.send_new_listings_email") as mock_notify:
        run_daily.main()

    mock_notify.assert_not_called()


def test_main_sends_captcha_email_when_blocked(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(tmp_path / ".last_run_date"))
    monkeypatch.setenv("TOP_N", "30")
    monkeypatch.setattr(kleinanzeigen, "was_blocked", True)
    monkeypatch.setattr(immoscout, "was_blocked", False)
    monkeypatch.setattr(vr_immobilien, "was_blocked", False)

    monkeypatch.setattr(run_daily, "_read_top_n", lambda path, n: [])

    with patch("run_daily.load_and_store_data"), \
         patch("run_daily.send_captcha_needed_email") as mock_captcha, \
         patch("run_daily.send_new_listings_email") as mock_notify:
        run_daily.main()

    mock_captcha.assert_called_once_with(["kleinanzeigen"])
    mock_notify.assert_not_called()


def test_main_does_not_mark_the_day_when_a_platform_is_blocked(tmp_path, monkeypatch):
    last_run_file = tmp_path / ".last_run_date"
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(last_run_file))
    monkeypatch.setattr(kleinanzeigen, "was_blocked", True)
    monkeypatch.setattr(immoscout, "was_blocked", False)
    monkeypatch.setattr(vr_immobilien, "was_blocked", False)
    monkeypatch.setattr(run_daily, "_read_top_n", lambda _path, _n: [])

    with patch("run_daily.load_and_store_data"), \
         patch("run_daily.send_captcha_needed_email"):
        run_daily.main()

    assert not last_run_file.exists()


def test_main_sends_captcha_email_for_multiple_blocked_platforms(tmp_path, monkeypatch):
    monkeypatch.setattr(run_daily, "_LAST_RUN_FILE", str(tmp_path / ".last_run_date"))
    monkeypatch.setenv("TOP_N", "30")
    monkeypatch.setattr(kleinanzeigen, "was_blocked", True)
    monkeypatch.setattr(immoscout, "was_blocked", True)
    monkeypatch.setattr(vr_immobilien, "was_blocked", False)

    monkeypatch.setattr(run_daily, "_read_top_n", lambda path, n: [])

    with patch("run_daily.load_and_store_data"), \
         patch("run_daily.send_captcha_needed_email") as mock_captcha, \
         patch("run_daily.send_new_listings_email"):
        run_daily.main()

    blocked_arg = mock_captcha.call_args[0][0]
    assert "kleinanzeigen" in blocked_arg
    assert "immoscout" in blocked_arg
    assert "vr_immobilien" not in blocked_arg
