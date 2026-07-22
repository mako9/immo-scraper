import json
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import src.browser as browser


def test_save_cookies_writes_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(browser, "_COOKIES_DIR", tmp_path)
    mock_driver = MagicMock()
    mock_driver.get_cookies.return_value = [{"name": "session", "value": "abc"}]
    browser.save_cookies(mock_driver, "test_platform")
    cookie_file = tmp_path / "cookies_test_platform.json"
    assert cookie_file.exists()
    assert json.loads(cookie_file.read_text()) == [{"name": "session", "value": "abc"}]


def test_load_cookies_injects_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(browser, "_COOKIES_DIR", tmp_path)
    (tmp_path / "cookies_test_platform.json").write_text(
        json.dumps([{"name": "session", "value": "abc"}])
    )
    mock_driver = MagicMock()
    browser.load_cookies(mock_driver, "test_platform", "https://example.com")
    mock_driver.get.assert_called_once_with("https://example.com")
    mock_driver.add_cookie.assert_called_once_with({"name": "session", "value": "abc"})


def test_load_cookies_skips_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(browser, "_COOKIES_DIR", tmp_path)
    mock_driver = MagicMock()
    browser.load_cookies(mock_driver, "missing", "https://example.com")
    mock_driver.get.assert_not_called()
    mock_driver.add_cookie.assert_not_called()


def test_wait_for_element_returns_true_when_found():
    mock_driver = MagicMock()
    with patch("src.browser.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.return_value = MagicMock()
        result = browser.wait_for_element(mock_driver, By.ID, "el", timeout=1)
    assert result is True


def test_wait_for_element_returns_false_on_timeout():
    mock_driver = MagicMock()
    with patch("src.browser.WebDriverWait") as mock_wait:
        mock_wait.return_value.until.side_effect = TimeoutException()
        result = browser.wait_for_element(mock_driver, By.ID, "el", timeout=1)
    assert result is False
