#!/usr/bin/env python3
"""
News collector - fetches RSS feeds and stores raw news.
"""
import logging
import time
from typing import List, Dict
from datetime import datetime, timezone

from feeds.registry import FeedRegistry
from collectors.parser import RSSFeedParser
from collectors.deduplicator import ArticleDeduplicator
from storage.feed_repository import FeedRepository
from storage.raw_news_repository import RawNews, RawNewsRepository
from config import Config

logger = logging.getLogger(__name__)


class NewsCollector:
    """Collects news from RSS feeds and stores to Firestore."""

    def __init__(
        self,
        config: Config = None,
        feed_repo: FeedRepository = None,
        news_repo: RawNewsRepository = None,
    ):
        """Initialize news collector.

        Args:
            config: Configuration object
            feed_repo: Feed repository
            news_repo: Raw news repository
        """
        self.config = config or Config()
        self.feed_repo = feed_repo or FeedRepository(config=self.config)
        self.news_repo = news_repo or RawNewsRepository(config=self.config)
        self.parser = RSSFeedParser()
        self.deduplicator = ArticleDeduplicator()

    def collect(self, source_filter: List[str] = None) -> Dict[str, int]:
        """Collect news from all active RSS feeds.

        Args:
            source_filter: Optional list of source names to collect from

        Returns:
            Statistics dictionary
        """
        stats = {
            "sources_processed": 0,
            "sources_failed": 0,
            "articles_found": 0,
            "articles_stored": 0,
            "articles_skipped": 0,
            "start_time": datetime.now(timezone.utc),
        }

        # Get active feeds
        feeds = self.feed_repo.get_active_feeds()
        if source_filter:
            feeds = [f for f in feeds if f.name in source_filter]

        logger.info(f"Starting collection from {len(feeds)} active feeds")

        for feed in feeds:
            try:
                # Parse feed
                articles = self.parser.parse_feed(feed.url)
                stats["articles_found"] += len(articles)

                if not articles:
                    continue

                # Convert to RawNews objects
                raw_news_list = []
                for article in articles:
                    raw_news = RawNews(
                        title=article["title"],
                        description=article["description"],
                        snippet_text=article["snippet_text"],
                        source=feed.name,
                        url=article["url"],
                        published_at=article["published_at"],
                        language="en",
                    )
                    raw_news_list.append(raw_news)

                # Store to database (repository handles dedup)
                for news in raw_news_list:
                    news_id = self.news_repo.save(news)
                    if news_id:
                        stats["articles_stored"] += 1
                    else:
                        stats["articles_skipped"] += 1

                stats["sources_processed"] += 1
                logger.info(f"Processed {feed.name}: {len(articles)} articles")

                # Small delay between feeds
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to collect from {feed.name}: {e}")
                stats["sources_failed"] += 1

        stats["duration_seconds"] = (datetime.now(timezone.utc) - stats["start_time"]).total_seconds()

        # Log summary
        logger.info("=" * 50)
        logger.info("Collection Summary:")
        logger.info(f"  Duration: {stats['duration_seconds']:.2f}s")
        logger.info(f"  Sources processed: {stats['sources_processed']}")
        logger.info(f"  Sources failed: {stats['sources_failed']}")
        logger.info(f"  Articles found: {stats['articles_found']}")
        logger.info(f"  Articles stored: {stats['articles_stored']}")
        logger.info(f"  Articles skipped: {stats['articles_skipped']}")
        logger.info("=" * 50)

        return stats


# Legacy compatibility - keep old collector.py working
def run_legacy_collection():
    """Run collection using legacy collector.py for compatibility."""
    import sys
    from pathlib import Path

    # Run the old collector
    old_collector = Path(__file__).parent.parent / "collector.py"
    if old_collector.exists():
        import subprocess
        result = subprocess.run([sys.executable, str(old_collector)])
        return result.returncode == 0
    else:
        logger.error("Legacy collector.py not found")
        return False
