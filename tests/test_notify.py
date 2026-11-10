import base64
from email import message_from_bytes
from unittest.mock import MagicMock, patch

import pytest
import requests
from google.auth.exceptions import GoogleAuthError

from src.notify import send_captcha_needed_email, send_new_listings_email


@pytest.fixture(autouse=True)
def notify_env(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "sender@gmail.com")
    monkeypatch.setenv("NOTIFICATION_RECIPIENT", "recipient@gmail.com")


def _decoded_message(mock_post):
    payload = mock_post.call_args.kwargs["json"]
    raw = base64.urlsafe_b64decode(payload["raw"])
    return message_from_bytes(raw)


def _send(entries, top_n=30):
    with patch("src.notify._get_access_token", return_value="access-token"), \
         patch("src.notify.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        send_new_listings_email(entries, top_n)
        return mock_post


def _send_captcha(platforms=None):
    if platforms is None:
        platforms = ["kleinanzeigen"]
    with patch("src.notify._get_access_token", return_value="access-token"), \
         patch("src.notify.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        send_captcha_needed_email(platforms)
        return mock_post


def test_posts_to_gmail_api():
    mock_post = _send([("House A", "https://example.com/1")])
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def test_authenticates_with_access_token():
    mock_post = _send([("House A", "https://example.com/1")])
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer access-token"


def test_sends_message():
    mock_post = _send([("House A", "https://example.com/1")])
    mock_post.return_value.raise_for_status.assert_called_once()


def test_subject_contains_count_and_top_n():
    mock_post = _send([("A", "https://a.com"), ("B", "https://b.com")], top_n=15)
    msg = _decoded_message(mock_post)
    assert "2" in msg["Subject"]
    assert "15" in msg["Subject"]


def test_body_contains_all_titles_and_links():
    entries = [("House A", "https://example.com/1"), ("Land B", "https://example.com/2")]
    mock_post = _send(entries)
    body = _decoded_message(mock_post).get_payload()
    assert "House A" in body
    assert "https://example.com/1" in body
    assert "Land B" in body
    assert "https://example.com/2" in body


def test_from_and_to_headers():
    mock_post = _send([("X", "https://x.com")])
    msg = _decoded_message(mock_post)
    assert msg["From"] == "sender@gmail.com"
    assert msg["To"] == "recipient@gmail.com"


def test_warns_instead_of_raising_when_api_unreachable(capsys):
    with patch("src.notify._get_access_token", return_value="access-token"), \
         patch("src.notify.requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("connection reset")
        send_new_listings_email([("A", "https://a.com")], 30)
        assert "Warning" in capsys.readouterr().out


def test_warns_instead_of_raising_on_error_response(capsys):
    with patch("src.notify._get_access_token", return_value="access-token"), \
         patch("src.notify.requests.post") as mock_post:
        response = MagicMock(status_code=401)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("401")
        mock_post.return_value = response
        send_new_listings_email([("A", "https://a.com")], 30)
        assert "Warning" in capsys.readouterr().out


def test_warns_instead_of_raising_when_token_missing(capsys):
    with patch("src.notify._get_access_token", side_effect=FileNotFoundError("no token")):
        send_new_listings_email([("A", "https://a.com")], 30)
        assert "Warning" in capsys.readouterr().out


def test_warns_instead_of_raising_when_refresh_fails(capsys):
    with patch("src.notify._get_access_token", side_effect=GoogleAuthError("refresh failed")):
        send_new_listings_email([("A", "https://a.com")], 30)
        assert "Warning" in capsys.readouterr().out


def test_captcha_email_subject():
    mock_post = _send_captcha()
    msg = _decoded_message(mock_post)
    assert "kleinanzeigen" in msg["Subject"]


def test_captcha_email_subject_lists_all_platforms():
    mock_post = _send_captcha(["kleinanzeigen", "immoscout"])
    msg = _decoded_message(mock_post)
    assert "kleinanzeigen" in msg["Subject"]
    assert "immoscout" in msg["Subject"]


def test_captcha_email_body_contains_setup_commands():
    mock_post = _send_captcha(["kleinanzeigen", "immoscout", "vr_immobilien"])
    body = _decoded_message(mock_post).get_payload()
    assert "--setup kleinanzeigen" in body
    assert "--setup immoscout" in body
    assert "--setup vr_immobilien" in body


def test_captcha_email_headers():
    mock_post = _send_captcha()
    msg = _decoded_message(mock_post)
    assert msg["From"] == "sender@gmail.com"
    assert msg["To"] == "recipient@gmail.com"
