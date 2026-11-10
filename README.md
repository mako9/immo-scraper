# immo-scraper
Small python script to fetch and evaluate data from some immo websites.

## Prerequisites

- python3
- pip3
- poetry

## Setup .env file

Create `.env` file in at current directory and copy content from `.env.example` file. Specify the environment variables according to your needs before running the code.

## Install dependencies
This project use poetry package manager.

In terminal run:

```poetry install ```

## Run

In terminal run:

```poetry run python main.py ```

### Manual steps

immoscout.de has a captcha mechanism to avoid automated scraping. When running the scraping for immoscout a
Chrome browser window opens where you have to solve the captcha once for the whole scraping process for immoscout.

## Daily run with email notification

The scraper can run automatically once a day and send an email when new listings appear in the top N results.

### Additional .env variables

```
GMAIL_USER=you@gmail.com
NOTIFICATION_RECIPIENT=you@gmail.com
TOP_N=30
```

Emails are sent via the Gmail API over HTTPS rather than SMTP, since SMTP ports are often blocked on corporate networks. One-time setup:

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project, enable the **Gmail API**, and create an OAuth client ID of type **Desktop app**.
2. Download the client secret JSON and save it as `~/.immo-scraper/gmail_credentials.json`.
3. Run `python main.py --setup-gmail` once — a browser opens for you to grant the `gmail.send` scope for `GMAIL_USER`. The resulting token is saved to `~/.immo-scraper/gmail_token.json` and refreshed automatically afterwards; you only need to redo this if the token is revoked.

### Activate

```bash
mkdir -p ~/.logs
cp com.immo-scraper.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.immo-scraper.daily.plist
```

The job fires at 08:00 daily. If the machine is asleep at that time, launchd queues the run and fires it on next wake. Logs are written to `~/.logs/immo-scraper.log` and `~/.logs/immo-scraper.err`.

### Deactivate

```bash
launchctl unload ~/Library/LaunchAgents/com.immo-scraper.daily.plist
```
