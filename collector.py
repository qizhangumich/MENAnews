#!/usr/bin/env python3
"""
Sovereign News Collector

A pure news collection layer that:
- Reads configured RSS feeds
- Fetches all available entries
- Deduplicates by URL
- Stores NEW articles to Firestore

No filtering. No analysis. No AI.
Just collection and storage.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import time

import feedparser
from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP

from firebase_config import initialize_firestore, NEWS_COLLECTION


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('collector.log')
    ]
)
logger = logging.getLogger(__name__)


# Maximum retry attempts for failed feeds
MAX_RETRIES = 2

# Retry delay in seconds
RETRY_DELAY = 5


class NewsCollector:
    """Main news collection class."""

    def __init__(self, db: firestore.Client, rss_sources_path: str = "rss_sources.json"):
        """
        Initialize the news collector.

        Args:
            db: Firestore client instance
            rss_sources_path: Path to RSS sources JSON configuration
        """
        self.db = db
        self.rss_sources_path = rss_sources_path
        self.sources = self._load_sources()

    def _load_sources(self) -> List[Dict[str, str]]:
        """Load RSS sources from configuration file."""
        try:
            with open(self.rss_sources_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('sources', [])
        except FileNotFoundError:
            logger.error(f"RSS sources file not found: {self.rss_sources_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in RSS sources file: {e}")
            raise

    def _fetch_feed(self, url: str, retry_count: int = 0) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch a single RSS feed with retry logic.

        Args:
            url: RSS feed URL
            retry_count: Current retry attempt number

        Returns:
            Parsed feed data or None if failed
        """
        try:
            logger.debug(f"Fetching feed: {url}")
            feed = feedparser.parse(url)

            # Check if feed was parsed successfully
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parsing warning for {url}: {feed.bozo_exception}")

            if not feed.entries:
                logger.warning(f"No entries found in feed: {url}")
                return feed

            logger.info(f"Fetched {len(feed.entries)} entries from {url}")
            return feed

        except Exception as e:
            if retry_count < MAX_RETRIES:
                logger.warning(
                    f"Error fetching {url} (attempt {retry_count + 1}/{MAX_RETRIES + 1}): {e}. "
                    f"Retrying in {RETRY_DELAY} seconds..."
                )
                time.sleep(RETRY_DELAY)
                return self._fetch_feed(url, retry_count + 1)
            else:
                logger.error(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts: {e}")
                return None

    def _article_exists(self, url: str) -> bool:
        """
        Check if an article with the given URL already exists.

        Args:
            url: Article URL to check

        Returns:
            True if article exists, False otherwise
        """
        try:
            # Query for document with matching URL
            docs = self.db.collection(NEWS_COLLECTION).where('url', '==', url).limit(1).get()
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking if article exists: {e}")
            # Assume it doesn't exist on error to avoid missing articles
            return False

    def _store_article(self, article: Dict[str, str], source_name: str) -> bool:
        """
        Store a single article to Firestore.

        Args:
            article: Article data from RSS feed
            source_name: Name of the RSS source

        Returns:
            True if stored successfully, False otherwise
        """
        url = article.get('link', '')

        if not url:
            logger.warning("Article has no URL, skipping")
            return False

        # Check for duplicates
        if self._article_exists(url):
            logger.debug(f"Article already exists, skipping: {url}")
            return False

        try:
            # Parse published date
            published_at = None
            if hasattr(article, 'published_parsed') and article.published_parsed:
                published_at = datetime(*article.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(article, 'updated_parsed') and article.updated_parsed:
                published_at = datetime(*article.updated_parsed[:6], tzinfo=timezone.utc)

            # Prepare document data
            doc_data = {
                'title': article.get('title', ''),
                'url': url,
                'source': source_name,
                'description': article.get('description', ''),
                'fetched_at': SERVER_TIMESTAMP,
            }

            if published_at:
                doc_data['published_at'] = published_at

            # Store in Firestore
            doc_ref = self.db.collection(NEWS_COLLECTION).document()
            doc_ref.set(doc_data)

            logger.debug(f"Stored article: {article.get('title', 'Untitled')}")
            return True

        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return False

    def collect(self) -> Dict[str, int]:
        """
        Run the full collection process on all configured sources.

        Returns:
            Dictionary with statistics about the collection run
        """
        stats = {
            'sources_processed': 0,
            'sources_failed': 0,
            'articles_found': 0,
            'articles_stored': 0,
            'articles_skipped': 0,
        }

        logger.info(f"Starting news collection from {len(self.sources)} sources")
        start_time = datetime.now(timezone.utc)

        for source in self.sources:
            source_name = source.get('name', 'Unknown')
            source_url = source.get('url', '')

            if not source_url:
                logger.warning(f"Source {source_name} has no URL, skipping")
                continue

            logger.info(f"Processing source: {source_name}")

            # Fetch the feed
            feed = self._fetch_feed(source_url)

            if feed is None:
                stats['sources_failed'] += 1
                continue

            stats['sources_processed'] += 1

            # Process each entry
            for entry in feed.entries:
                stats['articles_found'] += 1

                if self._store_article(entry, source_name):
                    stats['articles_stored'] += 1
                else:
                    stats['articles_skipped'] += 1

        # Log summary
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("=" * 50)
        logger.info("Collection Summary:")
        logger.info(f"  Duration: {duration:.2f} seconds")
        logger.info(f"  Sources processed: {stats['sources_processed']}/{len(self.sources)}")
        logger.info(f"  Sources failed: {stats['sources_failed']}")
        logger.info(f"  Articles found: {stats['articles_found']}")
        logger.info(f"  Articles stored: {stats['articles_stored']}")
        logger.info(f"  Articles skipped (duplicates): {stats['articles_skipped']}")
        logger.info("=" * 50)

        return stats


def main():
    """Main entry point for the news collector."""
    try:
        # Initialize Firestore
        logger.info("Initializing Firebase Firestore...")
        db = initialize_firestore()
        logger.info("Firebase initialized successfully")

        # Initialize collector
        collector = NewsCollector(db)

        # Run collection
        stats = collector.collect()

        # Exit with success
        sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
