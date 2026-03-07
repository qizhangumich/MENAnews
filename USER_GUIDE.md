# MENA News Ranking Service - User Guide

A bilingual news ranking service for Middle East investment and sovereign wealth fund (SWF) related news.

## Overview

This service provides:
- **Daily Telegram Digest**: Top 10 news from past 24 hours (GMT+8 08:30)
- **Weekly Email Digest**: Top 60 news with bilingual (Chinese/English) summaries (every Friday)

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project > Project Settings > Service Accounts
3. Click "Generate Private Key"
4. Save as `firebase_service_account.json` in project root

### 3. Configure Environment

Create `.env` file:

```bash
# Firebase (Required)
GOOGLE_APPLICATION_CREDENTIALS=./firebase_service_account.json
FIREBASE_PROJECT_ID=menanews-4a30c
FIRESTORE_COLLECTION=news

# Telegram (Required for daily digest)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# SMTP Email (Required for weekly digest)
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_password
EMAIL_RECIPIENTS=recipient@example.com

# OpenAI (Required for bilingual summaries)
OPENAI_API_KEY=sk-...
```

---

## Running the Service

### From Project Root (Important!)

Always run from the project root directory (`49.news_clawbot/`), **NOT** from `src/`:

```bash
# Correct
cd d:/personal/ai_projects/49.news_clawbot
python -m src.main daily

# Wrong (will fail)
cd src
python main.py daily
```

### Commands

| Command | Description |
|---------|-------------|
| `python -m src.main daily` | Send daily Telegram digest (top 10) |
| `python -m src.main weekly` | Send weekly email digest (top 60, bilingual) |
| `python -m src.main test` | Test configuration and connection |

---

## Key Functions Explained

### 1. Daily Digest (`src/daily_digest.py`)

**What it does:**
1. Fetches articles from past 24 hours
2. Deduplicates by URL and title
3. Scores articles (relevance + importance)
4. Filters by relevance threshold (≥25)
5. Sends top 10 to Telegram

**Output:** Telegram message with:
- Article titles with scores
- Links to full articles
- Tags (SWF, IPO, M&A, etc.)

### 2. Weekly Digest (`src/weekly_digest.py`)

**What it does:**
1. Fetches articles from past 7 days (~400+ articles)
2. Scores and sorts by total score
3. Selects top 60 articles
4. **Generates bilingual summaries via OpenAI API** (takes 10-20 minutes)
5. Sends HTML email via SMTP

**Output:** Email with:
- Chinese and English titles for each article
- Chinese and English summaries
- Tags, source, and timestamp
- "Read more" links

### 3. Scoring System (`src/scoring.py`)

The system uses two scoring dimensions:

#### Relevance Score (0-100)
Content relevance to SWF/investment topics:

| Keyword | Points |
|---------|--------|
| SWF entities (Mubadala, ADIA, PIF, etc.) | +45 |
| "Sovereign wealth" | +35 |
| Family office | +30 |
| Fund/LP/GP/PE/VC | +20 |
| Deal terms (IPO, M&A) | +15 |
| Investment/financing | +10 |

#### Importance Score (0-100)
Source credibility and event impact:

| Component | Points |
|-----------|--------|
| **Source**: Reuters | +40 |
| **Source**: FT/WSJ/Bloomberg | +38 |
| **Event**: IPO/M&A | +35 |
| **Event**: Funding round | +30 |
| **Event**: Policy/Regulation | +25 |
| **Freshness**: <6 hours | +5 |

#### Total Score
```
TotalScore = 0.65 × RelevanceScore + 0.35 × ImportanceScore
```

### 4. OpenAI Summarizer (`src/summarizer.py`)

Generates bilingual summaries using OpenAI GPT:

**Features:**
- Chinese title translation
- 2-3 sentence Chinese summary focusing on GCC/SWF implications
- English title and summary
- Relevant tags in Chinese

**Fallback:** If OpenAI fails, uses rule-based translation with keyword substitution.

---

## How the Data Flows

```
┌─────────────────┐
│ RSS Feeds       │ (collector.py - separate service)
│ (Reuters, Zawya,│
│  The National,  │
│  etc.)          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Firestore       │ (articles stored here)
│ - news          │
│   collection    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Daily Digest    │     │ Weekly Digest    │
│ - Last 24h      │     │ - Last 7 days    │
│ - Top 10        │     │ - Top 60         │
│ - Telegram      │     │ - Email (SMTP)   │
└─────────────────┘     └──────────────────┘
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API keys and credentials |
| `rss_sources.json` | RSS feed list (for collector) |
| `src/config.py` | Scoring thresholds and limits |
| `firebase_service_account.json` | Firebase credentials |

---

## Common Issues & Solutions

### ImportError: attempted relative import

**Cause:** Running from `src/` directory instead of project root.

**Fix:**
```bash
cd ..  # Go to project root
python -m src.main weekly
```

### OpenAI API timeout

**Cause:** Processing 60 articles takes time.

**Solution:** Wait 10-20 minutes. Each article requires an API call.

### No relevant articles found

**Cause:** Relevance threshold too high.

**Fix:** Adjust `DAILY_RELEVANCE_THRESHOLD` in `.env` or `src/config.py`.

### Email not sending

**Check:**
1. SMTP credentials are correct
2. SMTP port is correct (465 for SSL, 587 for TLS)
3. Firewall isn't blocking SMTP

---

## GitHub Actions Setup

For automated execution, configure these secrets in your GitHub repo:

| Secret | Description |
|--------|-------------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full Firebase credentials JSON |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID |
| `OPENAI_API_KEY` | OpenAI API key for summaries |
| `SMTP_HOST` | SMTP server (e.g., smtp.163.com) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_RECIPIENTS` | Comma-separated email addresses |

---

## Development

### Project Structure

```
src/
├── main.py              # CLI entry point
├── config.py            # Configuration & env loading
├── firestore_client.py  # Firestore queries & models
├── scoring.py           # Relevance/importance scoring
├── summarizer.py        # OpenAI bilingual summaries
├── daily_digest.py      # Daily digest pipeline
├── weekly_digest.py     # Weekly digest pipeline
├── telegram_client.py   # Telegram bot integration
├── email_client.py      # SMTP email integration
└── extract.py           # URL/text extraction utilities
```

### Adding New Features

1. **New scoring keywords:** Edit `src/scoring.py` → `RELEVANCE_KEYWORDS` or `EVENT_KEYWORDS`
2. **Change article count:** Edit `src/config.py` → `daily_top_n` or modify `weekly_digest.py` → `[:60]`
3. **Add new sources:** Edit `rss_sources.json` (for collector) or `scoring.py` → `SOURCE_WEIGHTS`

---

## Support

For issues or questions:
- Check logs: `ranking_service.log` in project root
- Run `python -m src.main test` to verify configuration
- Review `.env` settings
