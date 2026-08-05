import os
import smtplib
import ssl
from email.message import EmailMessage


def _send(msg: EmailMessage) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    context = ssl.create_default_context()
    errors = []
    for mode, port in [("ssl", 465), ("starttls", 587)]:
        try:
            if mode == "ssl":
                with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as smtp:
                    smtp.login(gmail_user, app_password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP("smtp.gmail.com", port) as smtp:
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.login(gmail_user, app_password)
                    smtp.send_message(msg)
            return
        except (ConnectionResetError, smtplib.SMTPServerDisconnected, OSError) as exc:
            errors.append(exc)
    raise errors[-1]


def _send_or_warn(msg: EmailMessage) -> None:
    try:
        _send(msg)
    except Exception as exc:
        print(f"Warning: could not send email (network may be blocking SMTP): {exc}")


def send_new_listings_email(new_entries: list[tuple[str, str]], top_n: int) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    recipient = os.getenv("NOTIFICATION_RECIPIENT")

    n = len(new_entries)
    msg = EmailMessage()
    msg["Subject"] = f"[Immo] {n} new top-{top_n} listing(s)"
    msg["From"] = gmail_user
    msg["To"] = recipient

    lines = [f"New listings in your top {top_n}:\n"]
    for title, link in new_entries:
        lines.append(f"• {title} – {link}")
    msg.set_content("\n".join(lines))

    _send_or_warn(msg)


def send_captcha_needed_email(platforms: list[str]) -> None:
    gmail_user = os.getenv("GMAIL_USER")
    recipient = os.getenv("NOTIFICATION_RECIPIENT")

    names = ", ".join(platforms)
    msg = EmailMessage()
    msg["Subject"] = f"[Immo] Action needed: captcha on {names}"
    msg["From"] = gmail_user
    msg["To"] = recipient

    lines = ["The following platform(s) blocked the scraper:\n"]
    for platform in platforms:
        lines.append(f"  python main.py --setup {platform}")
    lines.append("\nRun the above command(s) to refresh your session(s).")
    msg.set_content("\n".join(lines))

    _send_or_warn(msg)
