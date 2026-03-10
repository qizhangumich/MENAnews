# Migration Notes: v1 to v2

This document guides you through migrating from the old MENA News system to the new modular v2 architecture.

## Overview of Changes

### Architecture Changes

| Aspect | v1 | v2 |
|--------|----|----|
| Structure | Monolithic scripts | Modular with clear separation |
| Data Storage | Single `news` collection | Separate collections for raw/scores/selection |
| Daily Digest | Sends all articles | Filtered candidates + human selection |
| Weekly Report | Top 60 with summaries | Structured sections 四、五、九 |
| Telegram | Simple text messages | Inline keyboard buttons |

### New Firestore Collections

```
v1:
├── news (everything mixed)

v2:
├── feed_sources       # RSS feed configs
├── news_raw          # Raw collected news only
├── news_scores       # Computed scores (separate)
├── news_selection    # Human selections from Telegram
├── telegram_push_log # Push tracking
├── weekly_reports    # Generated reports
└── system_config     # Editable weights
```

## Migration Steps

### Step 1: Backup Existing Data

Before migration, backup your Firestore data:

```bash
# Use gcloud to export
gcloud firestore export gs://your-backup-bucket/mena-backup --collection-ids=news
```

### Step 2: Deploy New Collections

The new system will automatically create collections when first run. No manual schema setup needed.

### Step 3: Migrate Existing News (Optional)

If you want to preserve existing news, create `jobs/migrate_v1_to_v2.py`:

```python
#!/usr/bin/env python3
"""Migration script from v1 to v2."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.cloud import firestore
from storage.raw_news_repository import RawNews, RawNewsRepository
from datetime import datetime, timezone

def migrate_news():
    """Migrate existing news from 'news' to 'news_raw'."""
    client = firestore.Client(project="menanews-4a30c")
    old_collection = client.collection("news")
    repo = RawNewsRepository()

    count = 0
    for doc in old_collection.stream():
        data = doc.to_dict()

        # Create RawNews object
        raw_news = RawNews(
            title=data.get("title", ""),
            description=data.get("description", ""),
            snippet_text=data.get("snippet_text", ""),
            source=data.get("source", ""),
            url=data.get("url", ""),
            published_at=data.get("published_at"),
            fetched_at=data.get("fetched_at", datetime.now(timezone.utc)),
            tags=data.get("tags", []),
            language="en",
        )

        # Save with old doc ID for reference
        news_id = repo.save(raw_news)
        if news_id:
            count += 1
            print(f"Migrated: {raw_news.title[:50]}")

    print(f"\nMigrated {count} articles to news_raw")

if __name__ == "__main__":
    migrate_news()
```

Run:
```bash
python jobs/migrate_v1_to_v2.py
```

### Step 4: Update GitHub Secrets

No changes needed - existing secrets work for v2.

New secret (optional):
- `OPENAI_API_KEY` - For enhanced weekly reports (section 九)

### Step 5: Update GitHub Actions

The new workflow file is `.github/workflows/mena-news-system.yml`.

To update:
1. Rename old workflow to disable it
2. Enable new workflow

```bash
# Disable old
mv .github/workflows/scheduler.yml .github/workflows/scheduler.yml.disabled

# New workflow is already in place
```

### Step 6: Update Commands

Old:
```bash
python -m src.main daily
python -m src.main weekly
```

New:
```bash
python app.py daily-push
python app.py weekly
```

## Feature Comparison

### Daily Digest

| Feature | v1 | v2 |
|---------|----|----|
| Articles sent | All from past 24h | Filtered candidates (score threshold) |
| Format | Bilingual summaries | Score display + selection buttons |
| User interaction | None | Inline keyboard (选四/选五/忽略) |
| Purpose | Reading | Selection for weekly report |

### Weekly Report

| Feature | v1 | v2 |
|---------|----|----|
| Content | Top 60 articles | Selected articles only |
| Structure | Simple list | Sections 四、五、九 |
| Section 九 | Not available | AI-generated strategic reflection |
| Source | Machine ranking | Human selection overrides |

## Rollback Plan

If you need to rollback to v1:

1. Disable v2 workflow:
   ```bash
   mv .github/workflows/mena-news-system.yml .github/workflows/mena-news-system.yml.disabled
   ```

2. Re-enable v1 workflow:
   ```bash
   mv .github/workflows/scheduler.yml.disabled .github/workflows/scheduler.yml
   ```

3. Use old commands:
   ```bash
   python -m src.main daily
   python -m src.main weekly
   ```

## Troubleshooting

### Issue: Old collection not found

**Solution**: The old system used `news` collection. v2 uses `news_raw`. Either:
- Run migration script
- Or start fresh with v2 (recommended for clean data)

### Issue: Telegram bot not responding

**Solution**: v2 uses python-telegram-bot v20+ with async. Make sure dependencies are updated:
```bash
pip install --upgrade python-telegram-bot
```

### Issue: Weekly report has no selections

**Solution**: Users need to select articles via Telegram first. Check:
1. Daily push is working
2. Users are clicking buttons
3. Check `news_selection` collection

## Next Steps After Migration

1. **Test Daily Push**: Run `python app.py daily-push` and verify Telegram buttons work
2. **Make Selections**: Use Telegram buttons to select some articles
3. **Test Weekly**: Run `python app.py weekly` to generate report
4. **Monitor**: Check Firestore collections are being populated correctly
5. **Tune Weights**: Adjust `config.py` scoring weights based on results
