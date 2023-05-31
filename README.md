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
