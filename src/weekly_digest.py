#!/usr/bin/env python3
"""
Weekly digest module for processing and sending weekly email digest.

Coordinates fetching, scoring, clustering, and sending weekly news.
"""

import logging
from datetime import datetime, timezone, timedelta

from .config import get_config
from .firestore_client import FirestoreClient, NewsArticle
from .extract import extract_first_article_url, html_to_text
from .scoring import score_articles, deduplicate_articles
from .topic_cluster import cluster_articles_by_topic, get_top_topics
from .email_client import send_weekly_digest

logger = logging.getLogger(__name__)


def run_weekly_digest() -> dict:
    """Run the complete weekly digest pipeline.

    Returns:
        Dictionary with execution results.
    """
    config = get_config()

    # Validate config
    try:
        config.validate()
        config.validate_email()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return {
            "success": False,
            "error": str(e),
            "articles_processed": 0,
            "topics_sent": 0,
        }

    logger.info("Starting weekly digest pipeline")

    # Initialize Firestore client
    db = FirestoreClient()
    db.connect()

    # Fetch articles from past 7 days
    logger.info("Fetching articles from Firestore...")
    articles = db.query_weekly_articles(days_back=7, limit=config.weekly_max_docs)

    if not articles:
        logger.warning("No articles found in the past 7 days")
        return {
            "success": True,
            "articles_processed": 0,
            "topics_sent": 0,
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

    # Filter out low-relevance articles for weekly digest
    # Use a slightly lower threshold for weekly (more inclusive)
    logger.info("Filtering articles for weekly digest...")
    relevant_articles = [a for a in articles if (a.relevance_score or 0) >= 15]

    if not relevant_articles:
        logger.warning("No relevant articles found")
        return {
            "success": True,
            "articles_processed": len(articles),
            "topics_sent": 0,
            "message": "No relevant articles found",
        }

    logger.info(f"Found {len(relevant_articles)} relevant articles")

    # Cluster by topic
    logger.info("Clustering articles by topic...")
    topics = cluster_articles_by_topic(relevant_articles)

    # Get top topics
    logger.info("Selecting top topics...")
    top_topics = get_top_topics(topics, n=config.weekly_top_topics)

    logger.info(f"Top {len(top_topics)} topics selected")

    # Log top topics
    for i, topic in enumerate(top_topics, 1):
        logger.info(f"{i}. [{topic.total_topic_score:.1f}] {topic.topic_key} ({topic.article_count} articles)")

    # Optionally write back scores to Firestore
    logger.info("Updating Firestore with computed scores...")
    updated_count = 0
    for article in relevant_articles[:100]:  # Limit updates
        if db.update_article_scores(article):
            updated_count += 1
    logger.info(f"Updated {updated_count} articles in Firestore")

    # Send weekly digest
    logger.info("Sending weekly digest email...")
    digest_date = datetime.now(timezone.utc)
    email_success = send_weekly_digest(top_topics, digest_date)

    result = {
        "success": email_success,
        "articles_processed": len(articles),
        "relevant_articles": len(relevant_articles),
        "topics_found": len(topics),
        "topics_sent": len(top_topics),
        "top_topics": [
            {
                "title": t.topic_key,
                "score": t.total_topic_score,
                "articles": t.article_count,
            }
            for t in top_topics
        ],
        "email_status": "sent" if email_success else "failed",
    }

    logger.info(f"Weekly digest pipeline completed. Success: {email_success}")
    return result
