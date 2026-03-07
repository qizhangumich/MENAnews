# MENA News Collector & Ranking Service

A complete news collection and ranking system for Middle East economic and sovereign-related news.

## Features

### News Collection (collector.py / scheduler.py)
- Reads configured RSS feeds
- Fetches all available entries
- Deduplicates by URL
- Stores new articles to Firebase Firestore
- Runs periodically (every 1 hour by default)

### News Ranking Service (src/)
- **Daily Telegram Digest**: Top 10 news from past 24 hours, sent at GMT+8 08:00
- **Weekly Email Digest**: Top 60 articles with bilingual (Chinese/English) summaries via OpenAI API, sent every Friday at GMT+8 08:00
- Relevance scoring based on SWF entities, investment keywords, and deal terms
- Importance scoring based on source credibility, event type, and freshness
- SMTP email delivery (163.com) with bilingual HTML templates

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Firebase

Download your Firebase service account key:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project > Project Settings > Service Accounts
3. Click "Generate Private Key"
4. Save the JSON file as `firebase_service_account.json` in the project root

### 3. Configure Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Required variables:
```bash
# Firebase
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase_service_account.json
FIREBASE_PROJECT_ID=menanews-4a30c
FIRESTORE_COLLECTION=news

# Telegram (for daily digest)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email (for weekly digest - SMTP)
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_password
EMAIL_RECIPIENTS=recipient@example.com,another@example.com

# Optional: OpenAI for enhanced summaries
OPENAI_API_KEY=sk-...
```

---

## Usage

### News Collection

**Run once:**
```bash
python collector.py
```

**Run scheduled (hourly):**
```bash
python scheduler.py
```

### News Ranking Service

**Run daily digest (Telegram):**
```bash
python -m src.main daily
```

**Run weekly digest (Email):**
```bash
python -m src.main weekly
```

**Test configuration:**
```bash
python -m src.main test
```

---

## Deployment

### GitHub Actions (12-hourly collection)

The project includes a GitHub Actions workflow for automated news collection. Configure these secrets in your repo settings:

- `FIREBASE_SERVICE_ACCOUNT_JSON` - Your Firebase credentials (entire JSON content)
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Telegram chat ID

### Cloud Run + Cloud Scheduler (Recommended)

1. **Deploy to Cloud Run:**
```bash
gcloud run deploy mena-news-service \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

2. **Create Cloud Scheduler jobs:**

For daily digest (GMT+8 08:30 = UTC 00:30):
```bash
gcloud scheduler jobs create http daily-digest \
  --schedule "30 0 * * *" \
  --time-zone "UTC" \
  --http-method=POST \
  --uri=https://your-service-url/run/daily \
  --oidc-service-account-email=your-service-account
```

For weekly digest (Friday GMT+8 08:30 = UTC 00:30):
```bash
gcloud scheduler jobs create http weekly-digest \
  --schedule "30 0 * * 5" \
  --time-zone "UTC" \
  --http-method=POST \
  --uri=https://your-service-url/run/weekly \
  --oidc-service-account-email=your-service-account
```

### Systemd Service (Linux)

Create `/etc/systemd/system/mena-news.service`:

```ini
[Unit]
Description=MENA News Collector
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/49.news_clawbot
Environment="GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase_service_account.json"
ExecStart=/usr/bin/python3 scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mena-news
sudo systemctl start mena-news
```

---

## Configuration

### Add/Remove RSS Sources

Edit `rss_sources.json`:

```json
{
  "sources": [
    {
      "name": "Source Name",
      "url": "https://example.com/rss"
    }
  ]
}
```

### Scoring Thresholds

Edit environment variables:

```bash
# Daily digest settings
DAILY_RELEVANCE_THRESHOLD=25
DAILY_TOP_N=10

# Weekly digest settings
WEEKLY_TOP_TOPICS=10
```

---

## Scoring System

### Relevance Score (0-100)

Based on content matching user interests:
- **SWF entities** (Mubadala, ADIA, PIF, etc.): +45
- **Sovereign wealth/SWF**: +35
- **Family office**: +30
- **Fund/LP/GP/PE/VC**: +20
- **Deal terms** (IPO, M&A): +15
- **Investment/financing**: +10

### Importance Score (0-100)

Based on source credibility and impact:
- **Source weight**: Reuters (40), FT/WSJ/Bloomberg (38), The National (30), etc.
- **Event weight**: IPO/M&A (35), Funding (30), Fund launch (28), Policy (25)
- **Entity weight**: SWF (20), Major bank (12), Regulator (10)
- **Freshness**: Articles <6h get +5 bonus

### Total Score

```
TotalScore = 0.65 × RelevanceScore + 0.35 × ImportanceScore
```

---

## Project Structure

```
49.news_clawbot/
├── collector.py              # News collection
├── scheduler.py              # Hourly scheduler
├── firebase_config.py        # Firebase initialization
├── rss_sources.json          # RSS feed configuration
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── src/                     # Ranking service
│   ├── __init__.py
│   ├── main.py             # CLI entry point
│   ├── config.py           # Configuration
│   ├── firestore_client.py # Firestore queries
│   ├── extract.py          # URL/text extraction
│   ├── scoring.py          # Scoring logic
│   ├── topic_cluster.py    # Topic clustering
│   ├── daily_digest.py     # Daily digest pipeline
│   ├── weekly_digest.py    # Weekly digest pipeline
│   ├── telegram_client.py  # Telegram integration
│   └── email_client.py     # Email (Resend) integration
└── .github/workflows/
    └── scheduler.yml        # GitHub Actions workflow
```

---

## Firestore Schema

Collection: `news`

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Article title |
| `url` | string | Article URL (extracted from description) |
| `source` | string | RSS source name |
| `published_at` | timestamp | Publication date |
| `fetched_at` | timestamp | When fetched |
| `description` | string | HTML description snippet |
| `snippet_text` | string | Plain text description |
| `relevance_score` | float | Relevance score 0-100 |
| `importance_score` | float | Importance score 0-100 |
| `total_score` | float | Combined score |
| `tags` | array | Article tags (SWF, IPO, M&A, etc.) |

---

## Troubleshooting

### Firebase Authentication Error
Ensure `firebase_service_account.json` exists and `GOOGLE_APPLICATION_CREDENTIALS` is set.

### Telegram Not Sending
Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are correct.

### Email Not Sending
Verify SMTP credentials (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`) are configured.

### No Articles in Digest
- Check Firestore has articles with `published_at` in the time window
- Adjust scoring thresholds if too strict
- Check logs: `tail -f ranking_service.log`

---

## Safety Notes

- Never commit `firebase_service_account.json` to version control
- Use environment variables for all sensitive credentials
- Logs do not contain tokens or credentials
- `.gitignore` is configured to exclude sensitive files
