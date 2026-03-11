#!/usr/bin/env python3
"""
Feed source repository for managing RSS feed configurations.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from google.cloud import firestore
from storage.firestore_client import FirestoreClient
from config import Config

logger = logging.getLogger(__name__)


class FeedSource:
    """Feed source data model."""

    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "")
        self.url = kwargs.get("url", "")
        self.category = kwargs.get("category", "general")
        self.active = kwargs.get("active", True)
        self.priority = kwargs.get("priority", 0)
        self.created_at = kwargs.get("created_at")
        self.updated_at = kwargs.get("updated_at")

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "name": self.name,
            "url": self.url,
            "category": self.category,
            "active": self.active,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "FeedSource":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)


class FeedRepository:
    """Repository for feed source management."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize feed repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_feed_sources

    def get_active_feeds(self) -> List[FeedSource]:
        """Get all active RSS feeds.

        Returns:
            List of active FeedSource objects
        """
        try:
            query = (
                self.client.collection(self.collection_name)
                .where("active", "==", True)
                .order_by("priority", direction=firestore.Query.DESCENDING)
            )
            docs = query.stream()

            feeds = []
            for doc in docs:
                data = doc.to_dict()
                feeds.append(FeedSource(id=doc.id, **data))

            logger.info(f"Retrieved {len(feeds)} active feeds")
            return feeds

        except Exception as e:
            logger.error(f"Error fetching active feeds: {e}")
            # Return default feeds if collection doesn't exist yet
            return self._get_default_feeds()

    def _get_default_feeds(self) -> List[FeedSource]:
        """Get default RSS feeds when collection is not initialized.

        Returns:
            List of default FeedSource objects
        """
        import json
        from pathlib import Path

        # Try to load from rss_sources.json
        rss_sources_path = Path(__file__).parent.parent / "rss_sources.json"
        try:
            with open(rss_sources_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sources_list = data.get("sources", [])
        except Exception as e:
            logger.warning(f"Could not load rss_sources.json: {e}")
            # Fallback to hardcoded feeds
            sources_list = [
                {"name": "Reuters Middle East", "url": "https://www.reuters.com/world/middle-east/rss"},
                {"name": "Reuters Business", "url": "https://www.reuters.com/business/rss"},
            ]

        default_feeds = []
        for source in sources_list:
            feed = FeedSource(
                name=source["name"],
                url=source["url"],
                category="general",
                active=True,
                priority=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            default_feeds.append(feed)

        logger.info(f"Using {len(default_feeds)} default RSS feeds")
        return default_feeds

    def add_feed(self, feed: FeedSource) -> str:
        """Add a new feed source.

        Args:
            feed: FeedSource object

        Returns:
            Document ID
        """
        doc_ref = self.client.collection(self.collection_name).document()
        feed.created_at = datetime.now(timezone.utc)
        feed.updated_at = datetime.now(timezone.utc)
        doc_ref.set(feed.to_dict())
        logger.info(f"Added feed: {feed.name}")
        return doc_ref.id

    def update_feed(self, feed_id: str, feed: FeedSource) -> bool:
        """Update an existing feed.

        Args:
            feed_id: Document ID
            feed: Updated FeedSource object

        Returns:
            True if successful
        """
        try:
            feed.updated_at = datetime.now(timezone.utc)
            self.client.collection(self.collection_name).document(feed_id).set(feed.to_dict())
            logger.info(f"Updated feed: {feed.name}")
            return True
        except Exception as e:
            logger.error(f"Error updating feed {feed_id}: {e}")
            return False

    def deactivate_feed(self, feed_id: str) -> bool:
        """Deactivate a feed.

        Args:
            feed_id: Document ID

        Returns:
            True if successful
        """
        try:
            doc_ref = self.client.collection(self.collection_name).document(feed_id)
            doc_ref.update({"active": False, "updated_at": datetime.now(timezone.utc)})
            logger.info(f"Deactivated feed: {feed_id}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating feed {feed_id}: {e}")
            return False


# Legacy compatibility with existing rss_sources.json
class RSS_SOURCES:
    """Legacy RSS sources loader."""

    @staticmethod
    def get_sources() -> List[dict]:
        """Get RSS sources from rss_sources.json.

        Returns:
            List of source dictionaries
        """
        import json
        from pathlib import Path

        rss_file = Path(__file__).parent.parent / "rss_sources.json"
        if not rss_file.exists():
            logger.warning(f"RSS sources file not found: {rss_file}")
            return []

        try:
            with open(rss_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("sources", [])
        except Exception as e:
            logger.error(f"Error loading RSS sources: {e}")
            return []
