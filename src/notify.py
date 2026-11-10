import base64
import os
from email.message import EmailMessage
from pathlib import Path

import requests
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_FILE = Path.home() / ".immo-scraper" / "gmail_token.json"


def _get_access_token() -> str:
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"No Gmail token found at {TOKEN_FILE}. Run 'python main.py --setup-gmail' first."
        )
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes=GMAIL_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    return creds.token


def _send(subject: str, body: str) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    recipient = os.getenv("NOTIFICATION_RECIPIENT")

    msg = EmailMessage()
    msg["From"] = gmail_user
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    access_token = _get_access_token()
    encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    response = requests.post(
        GMAIL_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": encoded},
    )
    response.raise_for_status()


def _send_or_warn(subject: str, body: str) -> None:
    try:
        _send(subject, body)
    except (requests.RequestException, GoogleAuthError, FileNotFoundError) as exc:
        print(f"Warning: could not send email (network may be blocking the Gmail API): {exc}")


def send_new_listings_email(new_entries: list[tuple[str, str]], top_n: int) -> None:
    n = len(new_entries)
    subject = f"[Immo] {n} new top-{top_n} listing(s)"

    lines = [f"New listings in your top {top_n}:\n"]
    for title, link in new_entries:
        lines.append(f"• {title} – {link}")
    body = "\n".join(lines)

    _send_or_warn(subject, body)


def send_captcha_needed_email(platforms: list[str]) -> None:
    names = ", ".join(platforms)
    subject = f"[Immo] Action needed: captcha on {names}"

    lines = ["The following platform(s) blocked the scraper:\n"]
    for platform in platforms:
        lines.append(f"  python main.py --setup {platform}")
    lines.append("\nRun the above command(s) to refresh your session(s).")
    body = "\n".join(lines)

    _send_or_warn(subject, body)
