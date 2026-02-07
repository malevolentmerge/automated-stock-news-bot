# automated-stock-news-bot

This repository contains a Python script that automatically fetches stock news, analyzes market-moving events using Google Gemini AI, and posts a concise, actionable summary to a Discord channel. The bot is designed for professional investors who want a quick, scannable market brief after U.S. market close.

---

## Features

- Fetches headlines for a configurable list of tickers via Yahoo Finance RSS feeds.
- Filters and prioritizes the top market-moving news items using Gemini AI.
- Scrapes article content and generates an actionable Discord summary with:
  - Bold headers for tickers
  - 1–2 sentence key points per headline
  - Sentiment (Bullish / Neutral / Bearish)
- Automatically posts the summary to a Discord channel via webhook.
- Scheduled to run Monday–Friday after market close (4:30 PM EST) using GitHub Actions.

---

## Prerequisites

- Python 3.14+
- Discord webhook URL
- Google Gemini API key
- Dependencies listed in `requirements.txt`

---

## Installation


1. Create a virtual environment (optional but recommended):

`python -m venv venv`
`source venv/bin/activate`  # Linux/macOS

2. Install dependencies:

`pip install -r requirements.txt`

---

## Configuration

1. Set up your environment variables:

`export GEMINI_API_KEY="your_gemini_api_key"`
`export DISCORD_WEBHOOK_URL="your_discord_webhook_url"`

2. Optional: edit the `TICKERS` list in `main.py` to add or remove stock symbols.

---

## Running Locally

Simply run:

`python main.py`

The script will:

1. Fetch today’s stock news headlines for the configured tickers.
2. Use Gemini AI to select the top 10 most important stories.
3. Scrape article content for context.
4. Generate a concise Discord-ready summary.
5. Post the summary to your configured Discord webhook.

---

## GitHub Actions Automation

The bot is configured to run automatically using GitHub Actions:

- Schedule: Monday–Friday, 4:30 PM EST
- Workflow file: `.github/workflows/daily_market_brief.yml`
- Python version: 3.14
- Dependencies: Installed from `requirements.txt`

### Repository Secrets

Add the following repository secrets in GitHub:

- `GEMINI_API_KEY` – Your Google Gemini API key.
- `DISCORD_WEBHOOK_URL` – Your Discord channel webhook URL.

### Workflow Behavior

1. Fetches the latest headlines for the configured tickers.
2. Identifies top market-moving stories using AI.
3. Generates a professional, scannable Discord summary.
4. Posts to the Discord channel.

---

## Notes

- The bot truncates articles to the first ~5000 characters to save context tokens and speed up AI processing.
- Currently, the bot filters news by today’s date (UTC) to avoid posting outdated headlines.
- During daylight savings time (EDT), update the GitHub Actions cron schedule to match 4:30 PM local time.
- For personal use, repository secrets are sufficient; no need for environment secrets unless you want multiple environments.

---

## Contributing

This is a personal project, but feel free to fork or modify for your own use. Key enhancements could include:

- Adding new tickers or sources
- Improving AI prompt quality
- Adding holiday/market calendar awareness to skip posting on market holidays

---
