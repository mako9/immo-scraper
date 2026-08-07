import os
import datetime
import openpyxl
from dotenv import load_dotenv

load_dotenv()

import src.immoscout as immoscout
import src.kleinanzeigen as kleinanzeigen
import src.vr_immobilien as vr_immobilien
from main import load_and_store_data
from src.notify import send_captcha_needed_email, send_new_listings_email

_LAST_RUN_FILE = ".last_run_date"


def _already_ran_today() -> bool:
    if not os.path.exists(_LAST_RUN_FILE):
        return False
    with open(_LAST_RUN_FILE) as f:
        return f.read().strip() == str(datetime.date.today())


def _mark_ran_today() -> None:
    with open(_LAST_RUN_FILE, "w") as f:
        f.write(str(datetime.date.today()))


def _read_top_n(path: str, n: int) -> list[tuple[str, str]]:
    if not os.path.exists(path):
        return []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Houses"]
    entries = []
    for row in ws.iter_rows(min_row=2, max_row=n + 1, min_col=2, max_col=10, values_only=True):
        title, _, _, _, _, _, _, _, link = row
        if link:
            entries.append((title or "", link))
    wb.close()
    return entries


def main():
    if _already_ran_today():
        print("Already ran today, skipping")
        return

    top_n = int(os.getenv("TOP_N", "30"))
    xlsx_path = "immo-results.xlsx"

    old_entries = _read_top_n(xlsx_path, top_n)
    old_links = {link for _, link in old_entries}

    load_and_store_data()

    blocked = [
        name for name, mod in [
            ("kleinanzeigen", kleinanzeigen),
            ("immoscout", immoscout),
            ("vr_immobilien", vr_immobilien),
        ]
        if mod.was_blocked
    ]
    if blocked:
        print(f"Blocked platforms: {blocked} — sending captcha notification email")
        send_captcha_needed_email(blocked)
        return

    _mark_ran_today()

    new_entries = _read_top_n(xlsx_path, top_n)
    added = [(title, link) for title, link in new_entries if link not in old_links]

    if added:
        print(f"Sending email for {len(added)} new top-{top_n} listing(s)")
        send_new_listings_email(added, top_n)
    else:
        print("No new entries in top listing(s), skipping email")


if __name__ == "__main__":
    main()
