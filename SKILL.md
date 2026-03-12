---
name: mena_news_collector
description: Collects Middle East news from RSS sources and stores to Firebase. Runs hourly and sends Telegram notifications.
metadata: {"openclaw":{"emoji":"📰"}}
---
# MENA News Collector

## When to use
Use this skill whenever the user asks to:
- Collect/scrape/fetch MENA/Middle East news
- Run the news collector
- Check for news updates
- Get news summary

## Inputs
None required. Runs on scheduled basis (hourly).

## How to run (tool execution)
Run the local runner:
- `python3 {baseDir}/run.py`

The scheduler will:
1. Collect news from all RSS sources
2. Deduplicate by URL
3. Store new articles to Firestore
4. Send Telegram notification with summary

## Examples
- collect mena news
- run news collector
- fetch middle east news
- check news updates

## Environment Variables Required
- `TELEGRAM_BOT_TOKEN` - Telegram bot token for notifications
- `TELEGRAM_CHAT_ID` - Chat ID to send notifications to
