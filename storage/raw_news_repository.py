#!/usr/bin/env python3
"""
Raw news repository for storing collected news articles.
"""
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from google.cloud import firestore
from google.cloud.firestore import SERVER_TIMESTAMP
from storage.firestore_client import FirestoreClient
from config import Config

logger = logging.getLogger(__name__)


class RawNews:
    """Raw news article data model."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")  # Firestore document ID
        self.title = kwargs.get("title", "")
        self.description = kwargs.get("description", "")
        self.snippet_text = kwargs.get("snippet_text", "")
        self.source = kwargs.get("source", "")
        self.url = kwargs.get("url", "")
        self.published_at = kwargs.get("published_at")
        self.fetched_at = kwargs.get("fetched_at")
        self.tags = kwargs.get("tags", [])
        self.language = kwargs.get("language", "en")
        self.normalized_hash = kwargs.get("normalized_hash", "")

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "title": self.title,
            "description": self.description,
            "snippet_text": self.snippet_text,
            "source": self.source,
            "url": self.url,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at or SERVER_TIMESTAMP,
            "tags": self.tags,
            "language": self.language,
            "normalized_hash": self.normalized_hash,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "RawNews":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)

    def generate_hash(self) -> str:
        """Generate normalized hash for deduplication."""
        content = f"{self.url}|{self.title[:100]}"
        return hashlib.md5(content.encode()).hexdigest()


class RawNewsRepository:
    """Repository for raw news storage."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize raw news repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_news_raw

    def exists_by_url(self, url: str) -> bool:
        """Check if article with this URL already exists.

        Args:
            url: Article URL

        Returns:
            True if article exists
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("url", "==", url)
                .limit(1)
                .get()
            )
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking article existence: {e}")
            return False

    def exists_by_hash(self, hash_value: str) -> bool:
        """Check if article with this hash already exists.

        Args:
            hash_value: Normalized hash

        Returns:
            True if article exists
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("normalized_hash", "==", hash_value)
                .limit(1)
                .get()
            )
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking article by hash: {e}")
            return False

    def save(self, news: RawNews) -> Optional[str]:
        """Save a raw news article.

        Args:
            news: RawNews object

        Returns:
            Document ID if saved, None if duplicate or error
        """
        # Check for duplicate by URL
        if news.url and self.exists_by_url(news.url):
            logger.debug(f"Article already exists (URL): {news.url}")
            return None

        # Generate and check hash
        news.normalized_hash = news.generate_hash()
        if self.exists_by_hash(news.normalized_hash):
            logger.debug(f"Article already exists (hash): {news.title[:50]}")
            return None

        try:
            doc_ref = self.client.collection(self.collection_name).document()
            news.fetched_at = datetime.now(timezone.utc)
            doc_ref.set(news.to_dict())
            logger.debug(f"Saved article: {news.title[:50]}...")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return None

    def get_recent(self, hours_back: int = 24, limit: int = 500) -> List[RawNews]:
        """Get recent raw news articles.

        Args:
            hours_back: Hours to look back
            limit: Maximum number of articles

        Returns:
            List of RawNews objects
        """
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        try:
            # Use fetched_at for filtering (single index)
            docs = (
                self.client.collection(self.collection_name)
                .where("fetched_at", ">=", cutoff_time)
                .order_by("fetched_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .get()
            )

            articles = []
            for doc in docs:
                data = doc.to_dict()
                articles.append(RawNews(id=doc.id, **data))

            logger.info(f"Retrieved {len(articles)} articles from past {hours_back} hours")
            return articles

        except Exception as e:
            logger.error(f"Error fetching recent articles: {e}")
            return []

    def get_by_id(self, news_id: str) -> Optional[RawNews]:
        """Get article by ID.

        Args:
            news_id: Document ID

        Returns:
            RawNews object or None
        """
        try:
            doc = self.client.collection(self.collection_name).document(news_id).get()
            if doc.exists:
                data = doc.to_dict()
                return RawNews(id=doc.id, **data)
            return None
        except Exception as e:
            logger.error(f"Error fetching article {news_id}: {e}")
            return None
