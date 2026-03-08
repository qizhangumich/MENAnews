#!/usr/bin/env python3
"""
Daily digest module for processing and sending daily Telegram digest.

Coordinates fetching, scoring, filtering, and sending daily news.
"""

import logging
from datetime import datetime, timezone, timedelta

from .config import get_config
from .firestore_client import FirestoreClient, NewsArticle
from .extract import extract_first_article_url, html_to_text
from .scoring import score_articles, filter_and_rank_daily, deduplicate_articles
from .telegram_client import send_daily_digest
from .summarizer import OpenAISummarizer

logger = logging.getLogger(__name__)


def run_daily_digest() -> dict:
    """Run the complete daily digest pipeline.

    Returns:
        Dictionary with execution results.
    """
    config = get_config()

    # Validate config
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {
            "success": False,
            "error": str(e),
            "articles_processed": 0,
            "articles_sent": 0,
        }

    logger.info("Starting daily digest pipeline")

    # Initialize Firestore client
    db = FirestoreClient()
    db.connect()

    # Fetch articles from past 24 hours
    logger.info("Fetching articles from Firestore...")
    articles = db.query_daily_articles(hours_back=24, limit=config.daily_max_docs)

    if not articles:
        logger.warning("No articles found in the past 24 hours")
        return {
            "success": True,
            "articles_processed": 0,
            "articles_sent": 0,
            "message": "No articles found",
        }

    logger.info(f"Fetched {len(articles)} articles")

    # Extract URLs and text snippets
    logger.info("Extracting URLs and text snippets...")
    for article in articles:
        if not article.url and article.description:
            article.url = extract_first_article_url(article.description)
        if not article.snippet_text and article.description:
            article.snippet_text = html_to_text(article.description)

    # Deduplicate
    logger.info("Deduplicating articles...")
    articles = deduplicate_articles(articles)
    logger.info(f"After deduplication: {len(articles)} articles")

    # Use all articles (no filtering - send all new updates)
    articles_to_send = articles
    logger.info(f"Sending {len(articles_to_send)} articles")

    # Generate bilingual summaries using OpenAI
    logger.info("Generating bilingual summaries for daily digest...")
    summarizer = OpenAISummarizer()
    summaries = summarizer.summarize_articles_batch(articles_to_send)
    logger.info(f"Generated {len(summaries)} summaries")

    # Send daily digest
    logger.info("Sending daily digest to Telegram...")
    digest_date = datetime.now(timezone.utc)
    telegram_success = send_daily_digest(summaries, digest_date)

    result = {
        "success": telegram_success,
        "articles_processed": len(articles),
        "articles_sent": len(articles_to_send),
        "top_titles": [s.title_en for s in summaries],
        "telegram_status": "sent" if telegram_success else "failed",
    }

    logger.info(f"Daily digest pipeline completed. Success: {telegram_success}")
    return result
