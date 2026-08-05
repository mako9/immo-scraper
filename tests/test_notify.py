import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.notify import send_captcha_needed_email, send_new_listings_email


@pytest.fixture(autouse=True)
def notify_env(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "sender@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret")
    monkeypatch.setenv("NOTIFICATION_RECIPIENT", "recipient@gmail.com")


def _send(entries, top_n=30):
    with patch("src.notify.ssl.create_default_context"), \
         patch("src.notify.smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        send_new_listings_email(entries, top_n)
        return mock_smtp, mock_smtp_cls


def _send_captcha(platforms=None):
    if platforms is None:
        platforms = ["kleinanzeigen"]
    with patch("src.notify.ssl.create_default_context"), \
         patch("src.notify.smtplib.SMTP_SSL") as mock_smtp_cls:
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        send_captcha_needed_email(platforms)
        return mock_smtp, mock_smtp_cls


def test_connects_to_gmail_ssl():
    mock_smtp, mock_smtp_cls = _send([("House A", "https://example.com/1")])
    mock_smtp_cls.assert_called_once()
    args = mock_smtp_cls.call_args
    assert args[0][0] == "smtp.gmail.com"
    assert args[0][1] == 465


def test_logs_in_with_credentials():
    mock_smtp, _ = _send([("House A", "https://example.com/1")])
    mock_smtp.login.assert_called_once_with("sender@gmail.com", "secret")


def test_sends_message():
    mock_smtp, _ = _send([("House A", "https://example.com/1")])
    mock_smtp.send_message.assert_called_once()


def test_subject_contains_count_and_top_n():
    mock_smtp, _ = _send([("A", "https://a.com"), ("B", "https://b.com")], top_n=15)
    msg = mock_smtp.send_message.call_args[0][0]
    assert "2" in msg["Subject"]
    assert "15" in msg["Subject"]


def test_body_contains_all_titles_and_links():
    entries = [("House A", "https://example.com/1"), ("Land B", "https://example.com/2")]
    mock_smtp, _ = _send(entries)
    msg = mock_smtp.send_message.call_args[0][0]
    body = msg.get_payload()
    assert "House A" in body
    assert "https://example.com/1" in body
    assert "Land B" in body
    assert "https://example.com/2" in body


def test_from_and_to_headers():
    mock_smtp, _ = _send([("X", "https://x.com")])
    msg = mock_smtp.send_message.call_args[0][0]
    assert msg["From"] == "sender@gmail.com"
    assert msg["To"] == "recipient@gmail.com"


def test_falls_back_to_starttls_on_ssl_failure(capsys):
    with patch("src.notify.ssl.create_default_context"), \
         patch("src.notify.smtplib.SMTP_SSL") as mock_ssl_cls, \
         patch("src.notify.smtplib.SMTP") as mock_starttls_cls:
        mock_ssl_cls.return_value.__enter__.side_effect = ConnectionResetError
        mock_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_starttls = MagicMock()
        mock_starttls_cls.return_value.__enter__.return_value = mock_starttls
        send_new_listings_email([("A", "https://a.com")], 30)
        assert mock_ssl_cls.call_count == 1
        assert mock_starttls_cls.call_count == 1
        mock_starttls.send_message.assert_called_once()


def test_warns_instead_of_raising_when_all_ports_blocked(capsys):
    with patch("src.notify.ssl.create_default_context"), \
         patch("src.notify.smtplib.SMTP_SSL") as mock_ssl_cls, \
         patch("src.notify.smtplib.SMTP") as mock_starttls_cls:
        mock_ssl_cls.return_value.__enter__.side_effect = ConnectionResetError
        mock_ssl_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_starttls_cls.return_value.__enter__.side_effect = ConnectionResetError
        mock_starttls_cls.return_value.__exit__ = MagicMock(return_value=False)
        send_new_listings_email([("A", "https://a.com")], 30)
        assert "Warning" in capsys.readouterr().out


def test_captcha_email_subject():
    mock_smtp, _ = _send_captcha()
    msg = mock_smtp.send_message.call_args[0][0]
    assert "kleinanzeigen" in msg["Subject"]


def test_captcha_email_subject_lists_all_platforms():
    mock_smtp, _ = _send_captcha(["kleinanzeigen", "immoscout"])
    msg = mock_smtp.send_message.call_args[0][0]
    assert "kleinanzeigen" in msg["Subject"]
    assert "immoscout" in msg["Subject"]


def test_captcha_email_body_contains_setup_commands():
    mock_smtp, _ = _send_captcha(["kleinanzeigen", "immoscout", "vr_immobilien"])
    msg = mock_smtp.send_message.call_args[0][0]
    body = msg.get_payload()
    assert "--setup kleinanzeigen" in body
    assert "--setup immoscout" in body
    assert "--setup vr_immobilien" in body


def test_captcha_email_headers():
    mock_smtp, _ = _send_captcha()
    msg = mock_smtp.send_message.call_args[0][0]
    assert msg["From"] == "sender@gmail.com"
    assert msg["To"] == "recipient@gmail.com"
