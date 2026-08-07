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
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
NOTIFICATION_RECIPIENT=you@gmail.com
TOP_N=30
```

`GMAIL_APP_PASSWORD` must be a Gmail App Password, not your account password. Generate one at Google Account → Security → 2-Step Verification → App passwords.

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
