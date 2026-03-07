#!/usr/bin/env python3
"""
Weekly digest module for processing and sending weekly email digest.

Features top 60 news articles with bilingual (Chinese/English) summaries.
"""

import logging
from datetime import datetime, timezone, timedelta

from .config import get_config
from .firestore_client import FirestoreClient, NewsArticle
from .extract import extract_first_article_url, html_to_text
from .scoring import score_articles, deduplicate_articles
from .summarizer import OpenAISummarizer
from .email_client import send_weekly_digest

logger = logging.getLogger(__name__)


def run_weekly_digest() -> dict:
    """Run the complete weekly digest pipeline.

    Returns:
        Dictionary with execution results.
    """
    config = get_config()

    # Validate email config (only email needed for weekly digest)
    try:
        config.validate_email()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {
            "success": False,
            "error": str(e),
            "articles_processed": 0,
            "articles_sent": 0,
        }

    logger.info("Starting weekly digest pipeline")

    # Initialize Firestore client
    db = FirestoreClient()
    db.connect()

    # Fetch articles from past 7 days
    logger.info("Fetching articles from Firestore...")
    articles = db.query_weekly_articles(days_back=7, limit=2000)

    if not articles:
        logger.warning("No articles found in the past 7 days")
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

    # Score articles
    logger.info("Scoring articles...")
    articles = score_articles(articles)

    # Sort by total score and get top 60 (no filtering by relevance)
    logger.info("Selecting top 60 articles by total score...")
    top_articles = sorted(articles, key=lambda a: a.total_score or 0, reverse=True)[:60]

    logger.info(f"Top {len(top_articles)} articles selected")

    # Log top articles preview
    for i, article in enumerate(top_articles[:5], 1):
        logger.info(f"{i}. [{article.total_score:.1f}] {article.title[:60]}...")

    # Generate bilingual summaries using OpenAI
    logger.info("Generating bilingual summaries...")
    summarizer = OpenAISummarizer()
    summaries = summarizer.summarize_articles_batch(top_articles)

    logger.info(f"Generated {len(summaries)} summaries")

    # Optionally write back scores to Firestore
    logger.info("Updating Firestore with computed scores...")
    updated_count = 0
    for article in top_articles[:100]:  # Limit updates
        if db.update_article_scores(article):
            updated_count += 1
    logger.info(f"Updated {updated_count} articles in Firestore")

    # Send weekly digest
    logger.info("Sending weekly digest email...")
    digest_date = datetime.now(timezone.utc)
    email_success = send_weekly_digest(summaries, digest_date)

    result = {
        "success": email_success,
        "articles_processed": len(articles),
        "articles_sent": len(top_articles),
        "summaries_generated": len(summaries),
        "email_status": "sent" if email_success else "failed",
    }

    logger.info(f"Weekly digest pipeline completed. Success: {email_success}")
    return result
