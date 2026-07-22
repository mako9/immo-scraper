import json
import re
import subprocess
import zipfile
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_COOKIES_DIR = Path.home() / ".immo-scraper"
_CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def _chrome_major_version() -> int | None:
    try:
        out = subprocess.run([_CHROME_BINARY, "--version"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"(\d+)\.", out)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def get_driver(headless: bool = True) -> uc.Chrome:
    options = uc.ChromeOptions()
    try:
        return uc.Chrome(options=options, headless=headless, version_main=_chrome_major_version())
    except zipfile.BadZipFile:
        raise RuntimeError(
            "ChromeDriver download failed — likely a captive portal or no internet access. "
            "Authenticate on the network in your browser, then retry."
        )


def load_cookies(driver, platform_name: str, base_url: str) -> None:
    cookie_file = _COOKIES_DIR / f"cookies_{platform_name}.json"
    if not cookie_file.exists():
        return
    driver.get(base_url)
    with open(cookie_file) as f:
        cookies = json.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass


def save_cookies(driver, platform_name: str) -> None:
    _COOKIES_DIR.mkdir(exist_ok=True)
    cookie_file = _COOKIES_DIR / f"cookies_{platform_name}.json"
    with open(cookie_file, "w") as f:
        json.dump(driver.get_cookies(), f)


def wait_for_element(driver, by, name, timeout: int = 30) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, name))
        )
        return True
    except TimeoutException:
        return False
