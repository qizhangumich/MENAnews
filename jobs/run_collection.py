#!/usr/bin/env python3
"""
Job: Run news collection from RSS feeds.
Fetches raw articles and stores to Firestore (news_raw collection).
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.collector import NewsCollector
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run news collection job."""
    logger.info("=" * 60)
    logger.info("Starting News Collection Job")
    logger.info("=" * 60)

    config = Config()
    collector = NewsCollector(config=config)

    stats = collector.collect()

    logger.info("=" * 60)
    logger.info("Collection Job Complete")
    logger.info(f"Sources: {stats['sources_processed']}/{stats['sources_processed'] + stats['sources_failed']}")
    logger.info(f"Articles: {stats['articles_stored']} stored, {stats['articles_skipped']} skipped")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
