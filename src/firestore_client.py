#!/usr/bin/env python3
"""
Firestore client module for querying news articles.

Handles all Firestore operations for the MENA News Ranking Service.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import google.cloud.firestore as firestore
from google.cloud.firestore_v1.base_query import BaseQuery

from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    """News article data model."""

    doc_id: str
    title: str
    description: str
    source: str
    url: Optional[str] = None
    snippet_text: Optional[str] = None
    published_at: Optional[datetime] = None
    fetched_at: Optional[datetime] = None
    relevance_score: Optional[float] = None
    importance_score: Optional[float] = None
    total_score: Optional[float] = None
    tags: Optional[List[str]] = None

    @classmethod
    def from_doc(cls, doc_id: str, data: Dict[str, Any]) -> "NewsArticle":
        """Create NewsArticle from Firestore document."""
        published_at = data.get("published_at")
        if published_at and isinstance(published_at, datetime):
            # Ensure timezone aware
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=timezone.utc)

        fetched_at = data.get("fetched_at")
        if fetched_at and isinstance(fetched_at, datetime):
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=timezone.utc)

        return cls(
            doc_id=doc_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            source=data.get("source", ""),
            url=data.get("url"),
            snippet_text=data.get("snippet_text"),
            published_at=published_at,
            fetched_at=fetched_at,
            relevance_score=data.get("relevance_score"),
            importance_score=data.get("importance_score"),
            total_score=data.get("total_score"),
            tags=data.get("tags"),
        )

    def to_firestore_dict(self) -> Dict[str, Any]:
        """Convert to Firestore-compatible dict."""
        data = {}
        if self.url is not None:
            data["url"] = self.url
        if self.snippet_text is not None:
            data["snippet_text"] = self.snippet_text
        if self.relevance_score is not None:
            data["relevance_score"] = self.relevance_score
        if self.importance_score is not None:
            data["importance_score"] = self.importance_score
        if self.total_score is not None:
            data["total_score"] = self.total_score
        if self.tags is not None:
            data["tags"] = self.tags
        return data

    def get_effective_published_time(self) -> Optional[datetime]:
        """Get published_at, falling back to fetched_at."""
        return self.published_at or self.fetched_at


class FirestoreClient:
    """Client for querying and updating Firestore news collection."""

    def __init__(self, collection_name: Optional[str] = None):
        """Initialize Firestore client.

        Args:
            collection_name: Firestore collection name (defaults to config).
        """
        config = get_config()
        self.collection_name = collection_name or config.firestore_collection
        self.client: firestore.Client = None

    def connect(self) -> None:
        """Establish Firestore connection."""
        try:
            config = get_config()

            # Set credentials path if specified
            if config.google_credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.google_credentials_path
            else:
                # Try default locations
                default_paths = [
                    "firebase_service_account.json",
                    "config/firebase_service_account.json",
                    os.path.expanduser("~/.config/firebase_service_account.json"),
                ]
                for path in default_paths:
                    if os.path.exists(path):
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(path)
                        logger.info(f"Using credentials from: {path}")
                        break

            self.client = firestore.Client(project=config.firebase_project_id)
            logger.info(f"Connected to Firestore project: {config.firebase_project_id}")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
            raise

    def query_daily_articles(
        self,
        hours_back: int = 24,
        limit: int = 500
    ) -> List[NewsArticle]:
        """Query articles from the past N hours.

        Args:
            hours_back: Number of hours to look back.
            limit: Maximum number of documents to query.

        Returns:
            List of NewsArticle objects.
        """
        if self.client is None:
            self.connect()

        config = get_config()
        tz_offset = self._get_timezone_offset()

        # Calculate start time (in the configured timezone)
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=hours_back)

        logger.info(f"Querying articles from {start_time.isoformat()} to {now.isoformat()}")

        try:
            collection = self.client.collection(self.collection_name)

            # Query for documents published after start time
            # Note: Firestore indexes may need to be created for published_at
            query: BaseQuery = collection.where("published_at", ">=", start_time)

            # Also get documents without published_at (fallback to fetched_at)
            # We'll filter those in memory

            # Get results
            docs = list(query.stream())

            # Also fetch documents that might not have published_at but have recent fetched_at
            # This is a fallback for documents missing published_at
            fallback_query = (
                collection
                .where("fetched_at", ">=", start_time)
                .where("published_at", "==", None)  # Only those without published_at
            )
            fallback_docs = list(fallback_query.stream())

            # Combine and deduplicate
            all_docs = {d.id: d for d in docs + fallback_docs}

            # Convert to NewsArticle objects
            articles = []
            for doc_id, doc in all_docs.items():
                data = doc.to_dict()
                if data:
                    article = NewsArticle.from_doc(doc_id, data)
                    # Filter by effective published time
                    effective_time = article.get_effective_published_time()
                    if effective_time and effective_time >= start_time:
                        articles.append(article)

            # Sort by effective time (newest first)
            articles.sort(
                key=lambda a: a.get_effective_published_time() or datetime.min,
                reverse=True
            )

            # Apply limit
            articles = articles[:limit]

            logger.info(f"Retrieved {len(articles)} articles from daily query")
            return articles

        except Exception as e:
            logger.error(f"Error querying daily articles: {e}")
            # Fallback: get all recent documents by fetched_at
            return self._fallback_query(start_time, limit)

    def query_weekly_articles(
        self,
        days_back: int = 7,
        limit: int = 2000
    ) -> List[NewsArticle]:
        """Query articles from the past N days.

        Args:
            days_back: Number of days to look back.
            limit: Maximum number of documents to query.

        Returns:
            List of NewsArticle objects.
        """
        if self.client is None:
            self.connect()

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(days=days_back)

        logger.info(f"Querying articles from {start_time.isoformat()} to {now.isoformat()}")

        return self._fallback_query(start_time, limit)

    def _fallback_query(self, start_time: datetime, limit: int) -> List[NewsArticle]:
        """Fallback query using fetched_at when published_at index doesn't exist."""
        try:
            collection = self.client.collection(self.collection_name)
            docs = list(collection.where("fetched_at", ">=", start_time).stream())

            articles = []
            for doc in docs[:limit]:
                data = doc.to_dict()
                if data:
                    article = NewsArticle.from_doc(doc.id, data)
                    effective_time = article.get_effective_published_time()
                    if effective_time and effective_time >= start_time:
                        articles.append(article)

            articles.sort(
                key=lambda a: a.get_effective_published_time() or datetime.min,
                reverse=True
            )

            return articles[:limit]

        except Exception as e:
            logger.error(f"Fallback query also failed: {e}")
            return []

    def update_article_scores(
        self,
        article: NewsArticle,
        write_if_exists: bool = False
    ) -> bool:
        """Update article scores and computed fields in Firestore.

        Args:
            article: NewsArticle with computed scores.
            write_if_exists: If True, update even if fields already exist.

        Returns:
            True if update was successful.
        """
        if self.client is None:
            self.connect()

        try:
            doc_ref = self.client.collection(self.collection_name).document(article.doc_id)

            # Check if document exists and whether to update
            if not write_if_exists:
                doc = doc_ref.get()
                if doc.exists:
                    existing = doc.to_dict()
                    # Skip if scores already computed
                    if existing.get("total_score") is not None:
                        return False

            # Update with computed fields
            doc_ref.update(article.to_firestore_dict())
            logger.debug(f"Updated scores for article {article.doc_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating article {article.doc_id}: {e}")
            return False

    def _get_timezone_offset(self) -> int:
        """Get timezone offset for GMT+8 in hours."""
        return 8
