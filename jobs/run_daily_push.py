#!/usr/bin/env python3
"""
Job: Run daily Telegram push.
Sends scored candidate articles to Telegram for human selection.
"""
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.raw_news_repository import RawNewsRepository
from storage.score_repository import ScoreRepository
from storage.push_log_repository import PushLogRepository
from telegram.push_service import PushService
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run daily push job."""
    logger.info("=" * 60)
    logger.info("Starting Daily Push Job")
    logger.info("=" * 60)

    config = Config()
    news_repo = RawNewsRepository(config=config)
    score_repo = ScoreRepository(config=config)
    push_log_repo = PushLogRepository(config=config)
    push_service = PushService(config=config)

    # Get candidate scores
    threshold = config.thresholds.daily_push_threshold
    limit = config.telegram.daily_push_limit

    logger.info(f"Fetching candidates (score >= {threshold}, limit {limit})...")
    scores = score_repo.get_recent_candidates(
        hours_back=24,
        min_score=threshold,
        limit=limit * 2  # Get more to filter
    )

    if not scores:
        logger.warning("No candidates found")
        return 0

    logger.info(f"Found {len(scores)} candidate articles")

    # Get already pushed IDs
    pushed_ids = push_log_repo.get_pushed_news_ids()
    logger.info(f"Already pushed: {len(pushed_ids)} articles")

    # Filter and collect articles
    articles_to_push = []
    scores_to_push = []

    for score in scores:
        # Skip if already pushed
        if score.news_id in pushed_ids:
            continue

        # Get article
        article = news_repo.get_by_id(score.news_id)
        if not article:
            logger.warning(f"Article not found: {score.news_id}")
            continue

        articles_to_push.append(article)
        scores_to_push.append(score)

        if len(articles_to_push) >= limit:
            break

    if not articles_to_push:
        logger.info("No new articles to push")
        return 0

    logger.info(f"Pushing {len(articles_to_push)} articles to Telegram...")

    # Send to Telegram
    batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    stats = push_service.send_daily_digest_sync(
        articles=articles_to_push,
        scores=scores_to_push,
        batch_id=batch_id,
    )

    logger.info("=" * 60)
    logger.info("Daily Push Job Complete")
    logger.info(f"Sent: {stats['sent']}, Failed: {stats['failed']}, Skipped: {stats['skipped']}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
