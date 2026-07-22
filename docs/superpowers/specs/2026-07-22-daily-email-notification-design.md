# Daily Email Notification — Design Spec

**Date:** 2026-07-22
**Branch:** feature/email-notification

## Goal

Run the immo-scraper automatically once per day on the local macOS machine. If any listings appear in the top N (default 30) that were not there on the previous run, send a plain-text email via Gmail SMTP.

---

## Architecture

Three new artefacts; nothing existing is deleted.

```
main.py                                  (minor refactor: extract body into importable function)
src/notify.py                            (new: Gmail SMTP sender)
run_daily.py                             (new: daily orchestrator — diff + notify)
com.immo-scraper.daily.plist             (new: launchd agent, fires run_daily.py at 08:00)
```

### Flow in `run_daily.py`

1. Read `immo-results.xlsx` (Houses sheet, column J, rows 2–N+1) → `old_top_n_links` (empty set if file absent)
2. Import and call the scraper logic from `main.py` → overwrites `immo-results.xlsx`
3. Read the freshly written `immo-results.xlsx` → `new_top_n_links` with paired titles (column B)
4. `new_entries = new_top_n_links - old_top_n_links`
5. If `new_entries` is non-empty → call `src/notify.py` to send email; otherwise exit silently

---

## Components

### `main.py` — refactor

Extract the current `_load_and_store_data()` call site into an importable function so `run_daily.py` can call it without re-parsing CLI args. The `python main.py` entry point continues to work unchanged.

### `src/notify.py`

- Connects to `smtp.gmail.com:587` with STARTTLS
- Reads `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `NOTIFICATION_RECIPIENT` from the environment
- Accepts a list of `(title, link)` tuples
- Sends a plain-text email; subject: `[Immo] {n} new top-{N} listing(s)`
- Body: one bullet per entry — `• {title} – {link}`
- Errors propagate to stderr (captured by launchd)

### `run_daily.py`

- Standalone script, runs in the project root
- Reads `TOP_N` from `.env` (default: `30`)
- Handles the missing-file case (first run): old top N is treated as empty
- Handles fewer than N rated listings gracefully (compares however many exist)
- Notifications cover the Houses sheet only; Land listings are excluded

### launchd plist (`com.immo-scraper.daily.plist`)

Installed at `~/Library/LaunchAgents/com.immo-scraper.daily.plist`.

| Key | Value |
|-----|-------|
| `StartCalendarInterval` | `{Hour: 8, Minute: 0}` |
| `WorkingDirectory` | project root (absolute path) |
| `ProgramArguments` | `[".venv/bin/python", "run_daily.py"]` |
| `StandardOutPath` | `~/.logs/immo-scraper.log` |
| `StandardErrorPath` | `~/.logs/immo-scraper.err` |
| `EnvironmentVariables` | `PATH` set to include `.venv/bin` |

Missed runs (machine asleep at 08:00) are queued by launchd and fire on next wake.

**One-time setup commands:**
```bash
mkdir -p ~/.logs
launchctl load ~/Library/LaunchAgents/com.immo-scraper.daily.plist
```

---

## Environment Variables

New entries to add to `.env` and `.env.example`:

```
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFICATION_RECIPIENT=you@gmail.com
TOP_N=30
```

`GMAIL_APP_PASSWORD` must be a Gmail App Password (not the account password). Generate one at Google Account → Security → 2-Step Verification → App passwords.

---

## Error Handling

- SMTP failure → logged to stderr, script exits with non-zero code (visible in launchd logs)
- Scraper failure → existing behaviour (exception propagates, no Excel overwrite, no diff, no email)
- Missing `immo-results.xlsx` on first run → old top N treated as empty set, email sent with all top-N entries

---

## Out of Scope

- HTML email formatting
- Land listing notifications
- Persistent database of all-time seen listings
- Retry logic for SMTP failures
