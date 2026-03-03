---
name: sovereign_news_collector

description: >
This skill collects ALL news articles from configured RSS sources,
stores new articles into Firebase (Firestore),
and runs on a scheduled interval (e.g., hourly).

It does NOT filter, analyze, summarize, or score.
It only collects and stores news.

version: 1.0
author: Jeremy
---

# Sovereign News Collector Skill

## Purpose

Build a stable, independent news collection layer for Middle East economic and sovereign-related news.

This skill:

- Reads all configured RSS feeds
- Fetches all available entries
- Checks for duplicates (by URL)
- Stores only NEW articles into Firestore
- Runs periodically (e.g., every 1 hour)

No filtering.
No keyword matching.
No AI analysis.

This is a pure News Collection Layer.

---

## Architecture

RSS Sources  
→ Fetch entries  
→ Deduplicate by URL  
→ Store into Firebase  

---

## Configuration

RSS sources must be stored in:

rss_sources.json

Example structure:

{
  "sources": [
    {
      "name": "Reuters Middle East",
      "url": "https://www.reuters.com/world/middle-east/rss"
    },
    {
      "name": "Bloomberg Markets",
      "url": "https://feeds.bloomberg.com/markets/news.rss"
    }
  ]
}

This file can be expanded anytime.

---

## Storage Target

Firestore collection:

news

Each document must include:

- title
- url
- source
- published_at
- fetched_at
- description (if available)

---

## Deduplication Rule

Before inserting a document:

Check whether a document with the same URL already exists.

If exists:
    Skip insertion.

If not:
    Insert.

URL is the unique identifier.

---

## Execution Policy

- Designed to run every 1 hour
- Can be triggered manually
- Must not re-fetch already stored articles
- Must handle RSS errors gracefully
- Must continue processing other feeds even if one fails

---

## Expansion Rules

This skill must support:

- Adding new RSS sources without changing logic
- Removing RSS sources without breaking execution
- Scaling to 50+ feeds

---

## Error Handling

If an RSS feed fails:

- Log the error
- Continue to next feed
- Do NOT terminate entire execution

---

## Performance Expectations

Typical daily volume:

50–300 articles

System must remain lightweight and stable.

---

## Important Constraints

- No content scraping beyond RSS
- No AI processing
- No summarization
- No filtering
- No keyword extraction

This skill is strictly a News Collector.

Future layers (analysis, scoring, entity tracking) will be separate skills.