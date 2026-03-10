# MENA News Intelligence System v2

A modular Python system for collecting, scoring, and reporting Middle East investment and sovereign wealth fund (SWF) news.

## Overview

This system provides:
- **Automated RSS collection** from 21+ MENA business news sources
- **Intelligent scoring** for relevance and importance
- **Daily Telegram review** with inline keyboard buttons for human selection
- **Weekly reports** with sections: 募资市场动态, 投资者关注, 募资的思考和反思

## Architecture

```
mena_news_system/
├── app.py                   # Main entry point
├── config.py                # Central configuration
├── requirements.txt         # Dependencies
├── .env.example            # Environment template
│
├── feeds/                   # RSS feed management
│   └── registry.py         # Feed source registry
│
├── collectors/              # News collection
│   ├── collector.py        # Main collector
│   ├── parser.py           # RSS parser
│   └── deduplicator.py     # Deduplication
│
├── storage/                 # Firestore repositories
│   ├── firestore_client.py
│   ├── feed_repository.py
│   ├── raw_news_repository.py
│   ├── score_repository.py
│   ├── selection_repository.py
│   ├── push_log_repository.py
│   └── report_repository.py
│
├── scoring/                 # Scoring engine
│   ├── rules.py            # Scoring rules
│   └── engine.py           # Scoring engine
│
├── telegram/                # Telegram bot
│   ├── bot.py              # Main bot
│   ├── keyboards.py        # Inline keyboards
│   ├── formatter.py        # Message formatter
│   └── push_service.py     # Push service
│
├── reports/                 # Weekly reports
│   └── weekly_generator.py
│
├── email/                   # Email delivery
│   └── sender.py
│
└── jobs/                    # Scheduled jobs
    ├── run_collection.py
    ├── run_scoring.py
    ├── run_daily_push.py
    └── run_weekly_report.py
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Firebase
GOOGLE_APPLICATION_CREDENTIALS=./firebase_service_account.json
FIREBASE_PROJECT_ID=menanews-4a30c

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Email (SMTP)
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your_email@163.com
SMTP_PASSWORD=your_password
EMAIL_TO=recipient@example.com

# OpenAI (for weekly reports)
OPENAI_API_KEY=sk-your-key
```

### 3. Run Jobs

```bash
# Collect news from RSS feeds
python app.py collect

# Score articles
python app.py score

# Send daily Telegram push
python app.py daily-push

# Generate weekly report
python app.py weekly

# Run Telegram bot (interactive)
python app.py bot
```

## Firestore Collections

| Collection | Purpose |
|------------|---------|
| `feed_sources` | RSS feed configurations |
| `news_raw` | Raw collected news |
| `news_scores` | Computed scores |
| `news_selection` | Human selections from Telegram |
| `telegram_push_log` | Push tracking |
| `weekly_reports` | Generated reports |
| `system_config` | Editable weights |

## Daily Workflow

1. **Collection**: RSS feeds → `news_raw`
2. **Scoring**: `news_raw` → `news_scores`
3. **Telegram Push**: Candidates → Inline keyboard selection
4. **Human Selection**: User clicks buttons → `news_selection`

## Weekly Workflow

1. **Collect Selections**: Get `news_selection` for current week
2. **Generate Report**:
   - Section 4: 募资市场动态
   - Section 5: 投资者关注
   - Section 9: 募资的思考和反思
3. **Save & Email**: Store to `weekly_reports` and send via SMTP

## Scoring System

### Relevance Score (0-100)
- SWF entities: +45
- "Sovereign wealth"/SWF: +35
- Family office: +30
- Fund/LP/GP/PE/VC: +20
- Deal terms (IPO/M&A): +15

### Importance Score (0-100)
- Source: Reuters (+40), FT/WSJ/Bloomberg (+38)
- Event: IPO/M&A (+35), Funding (+30)
- Entity: SWF (+20), Major banks (+12)
- Freshness: <6h (+5) to >48h (+1)

### Total Score
```
total_machine_score = 0.65 * relevance + 0.35 * importance
final_priority_score = max(selection_score, total_machine_score)
```

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Help information |
| `/status` | Weekly selection stats |
| `/generate_weekly_report` | Generate weekly report manually |

## Telegram Selection Buttons

| Button | Action |
|--------|--------|
| 选四 | Add to Section 4 |
| 选四⭐ | Add to Section 4 + Star |
| 选五 | Add to Section 5 |
| 选五⭐ | Add to Section 5 + Star |
| 四五都选 | Add to both sections |
| 忽略 | Ignore article |

## GitHub Actions

Configure these secrets in your repository:

| Secret | Description |
|--------|-------------|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Full Firebase JSON |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID |
| `SMTP_HOST` | SMTP server |
| `SMTP_PORT` | SMTP port (465) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `EMAIL_TO` | Recipient email |
| `OPENAI_API_KEY` | OpenAI API key |

## Migration Notes

### From v1 to v2

1. **New Collections**: v2 uses separate collections (`news_raw`, `news_scores`, `news_selection`)

2. **Legacy Compatibility**: The old `news` collection can temporarily act as raw layer

3. **Data Migration**: Run migration script to move existing data:
   ```bash
   python jobs/migrate_v1_to_v2.py
   ```

4. **Telegram Bot**: v2 uses python-telegram-bot v20+ with async

5. **Weekly Reports**: Now structured with sections 四、五、九 instead of simple summaries
