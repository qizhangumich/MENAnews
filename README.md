# Sovereign News Collector

A pure news collection layer for Middle East economic and sovereign-related news.

## What It Does

- Reads configured RSS feeds
- Fetches all available entries
- Deduplicates by URL
- Stores NEW articles to Firebase Firestore
- Runs periodically (every 1 hour)

## What It Does NOT Do

- No filtering
- No keyword matching
- No AI analysis
- No summarization

This is a pure News Collection Layer.

---

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Firebase

Download your Firebase service account key:

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project > Project Settings > Service Accounts
3. Click "Generate Private Key"
4. Save the JSON file as `firebase_service_account.json` in the project root

### 3. Test the Setup

```bash
python collector.py
```

This will run a one-time collection of all RSS feeds and store new articles to Firestore.

---

## Usage

### Manual Collection

Run the collector once:

```bash
python collector.py
```

### Scheduled Collection (Hourly)

Run the scheduler:

```bash
python scheduler.py
```

Press `Ctrl+C` to stop.

### Systemd Service (Linux)

Create `/etc/systemd/system/news-collector.service`:

```ini
[Unit]
Description=Sovereign News Collector
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/49.news_clawbot
ExecStart=/usr/bin/python3 /path/to/49.news_clawbot/scheduler.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable news-collector
sudo systemctl start news-collector
```

### Windows Task Scheduler

Create a task that runs `scheduler.py` at system startup or logon.

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

### Adjust Collection Interval

Edit `scheduler.py` and change `SCHEDULE_INTERVAL_MINUTES`.

---

## Firestore Schema

Collection: `news`

Each document contains:

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Article title |
| `url` | string | Article URL (unique identifier) |
| `source` | string | RSS source name |
| `published_at` | timestamp | Publication date (if available) |
| `fetched_at` | timestamp | When the article was fetched |
| `description` | string | Article description/snippet (if available) |

---

## Logging

Logs are written to:
- Console (stdout)
- `collector.log` file

---

## Troubleshooting

### Firebase Authentication Error

Ensure `firebase_service_account.json` exists in the project root.

### RSS Feed Timeout

The default timeout is 30 seconds. Increase `RSS_TIMEOUT` in `collector.py` if needed.

### Duplicate Articles

Duplicates are detected by URL. If you see unexpected duplicates, check that different RSS sources aren't publishing the same content with different URLs.
