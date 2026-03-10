#!/usr/bin/env python3
"""
Selection repository for storing human selection decisions.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from google.cloud import firestore
from storage.firestore_client import FirestoreClient
from config import Config

logger = logging.getLogger(__name__)


def get_week_key() -> str:
    """Get current week key in format YYYY-Www.

    Returns:
        Week key string
    """
    from datetime import datetime
    now = datetime.now(timezone.utc)
    year = now.year
    week = now.isocalendar()[1]
    return f"{year}-W{week:02d}"


class NewsSelection:
    """News selection data model."""

    def __init__(self, **kwargs):
        self.news_id = kwargs.get("news_id", "")
        self.title = kwargs.get("title", "")
        self.url = kwargs.get("url", "")
        self.source = kwargs.get("source", "")
        self.week_key = kwargs.get("week_key", get_week_key())
        self.selected_sections = kwargs.get("selected_sections", [])  # ["4"], ["5"], ["4", "5"]
        self.starred = kwargs.get("starred", False)
        self.selection_score = kwargs.get("selection_score", 100)
        self.selected_at = kwargs.get("selected_at")
        self.selected_by = kwargs.get("selected_by", "user")
        self.selection_method = kwargs.get("selection_method", "telegram")
        self.note = kwargs.get("note", "")

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "news_id": self.news_id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "week_key": self.week_key,
            "selected_sections": self.selected_sections,
            "starred": self.starred,
            "selection_score": self.selection_score,
            "selected_at": self.selected_at or datetime.now(timezone.utc),
            "selected_by": self.selected_by,
            "selection_method": self.selection_method,
            "note": self.note,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "NewsSelection":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)


class SelectionRepository:
    """Repository for news selections."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize selection repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_news_selection

    def save(self, selection: NewsSelection) -> Optional[str]:
        """Save or update a selection.

        Args:
            selection: NewsSelection object

        Returns:
            Document ID if saved
        """
        try:
            # Check if selection exists
            existing = (
                self.client.collection(self.collection_name)
                .where("news_id", "==", selection.news_id)
                .where("week_key", "==", selection.week_key)
                .limit(1)
                .get()
            )

            if existing:
                doc_id = list(existing)[0].id
                self.client.collection(self.collection_name).document(doc_id).set(selection.to_dict())
                logger.debug(f"Updated selection: {selection.news_id}")
                return doc_id
            else:
                doc_ref = self.client.collection(self.collection_name).document()
                doc_ref.set(selection.to_dict())
                logger.debug(f"Saved selection: {selection.news_id}")
                return doc_ref.id

        except Exception as e:
            logger.error(f"Error saving selection: {e}")
            return None

    def get_by_news_id(self, news_id: str, week_key: Optional[str] = None) -> Optional[NewsSelection]:
        """Get selection by news ID.

        Args:
            news_id: Raw news document ID
            week_key: Week key (uses current week if not provided)

        Returns:
            NewsSelection object or None
        """
        if week_key is None:
            week_key = get_week_key()

        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("news_id", "==", news_id)
                .where("week_key", "==", week_key)
                .limit(1)
                .get()
            )

            if docs:
                doc = list(docs)[0]
                data = doc.to_dict()
                return NewsSelection(id=doc.id, **data)
            return None

        except Exception as e:
            logger.error(f"Error fetching selection for {news_id}: {e}")
            return None

    def get_week_selections(self, week_key: Optional[str] = None) -> List[NewsSelection]:
        """Get all selections for a week.

        Args:
            week_key: Week key (uses current week if not provided)

        Returns:
            List of NewsSelection objects
        """
        if week_key is None:
            week_key = get_week_key()

        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", week_key)
                .order("selected_at", direction=firestore.Query.DESCENDING)
                .get()
            )

            selections = []
            for doc in docs:
                data = doc.to_dict()
                selections.append(NewsSelection(id=doc.id, **data))

            logger.info(f"Retrieved {len(selections)} selections for week {week_key}")
            return selections

        except Exception as e:
            logger.error(f"Error fetching week selections: {e}")
            return []

    def get_by_section(self, section: str, week_key: Optional[str] = None) -> List[NewsSelection]:
        """Get selections for a specific section.

        Args:
            section: Section number ("4" or "5")
            week_key: Week key (uses current week if not provided)

        Returns:
            List of NewsSelection objects
        """
        if week_key is None:
            week_key = get_week_key()

        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", week_key)
                .where("selected_sections", "array_contains", section)
                .get()
            )

            selections = []
            for doc in docs:
                data = doc.to_dict()
                selections.append(NewsSelection(id=doc.id, **data))

            logger.info(f"Retrieved {len(selections)} selections for section {section}")
            return selections

        except Exception as e:
            logger.error(f"Error fetching section selections: {e}")
            return []
