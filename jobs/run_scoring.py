#!/usr/bin/env python3
"""
Job: Run scoring engine on un-scored articles.
Computes relevance and importance scores for raw news.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.raw_news_repository import RawNewsRepository
from storage.score_repository import ScoreRepository
from scoring.engine import ScoringEngine
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run scoring job."""
    logger.info("=" * 60)
    logger.info("Starting Scoring Job")
    logger.info("=" * 60)

    config = Config()
    news_repo = RawNewsRepository(config=config)
    score_repo = ScoreRepository(config=config)
    engine = ScoringEngine(config=config)

    # Get recent articles from past 24 hours
    logger.info("Fetching recent articles from past 24 hours...")
    articles = news_repo.get_recent(hours_back=24, limit=500)

    if not articles:
        logger.warning("No articles found for scoring")
        return 0

    logger.info(f"Found {len(articles)} articles to score")

    # Score articles
    logger.info("Computing scores...")
    scored = 0
    updated = 0
    skipped = 0

    for article in articles:
        # Check if already scored
        existing_score = score_repo.get_by_news_id(article.id)
        if existing_score:
            skipped += 1
            continue

        # Compute scores
        score = engine.score_article(article)
        score.news_id = article.id

        # Save to database
        if score_repo.save(score):
            scored += 1
            updated += 1
        else:
            logger.warning(f"Failed to save score for article {article.id}")

    logger.info("=" * 60)
    logger.info("Scoring Job Complete")
    logger.info(f"Scored: {scored}, Updated: {updated}, Skipped (existing): {skipped}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
