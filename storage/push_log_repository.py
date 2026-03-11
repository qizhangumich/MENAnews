#!/usr/bin/env python3
"""
Push log repository for tracking Telegram pushes.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Set
from google.cloud import firestore
from storage.firestore_client import FirestoreClient
from config import Config
from storage.selection_repository import get_week_key

logger = logging.getLogger(__name__)


class TelegramPushLog:
    """Telegram push log data model."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")  # Firestore document ID
        self.news_id = kwargs.get("news_id", "")
        self.telegram_message_id = kwargs.get("telegram_message_id", 0)
        self.week_key = kwargs.get("week_key", get_week_key())
        self.push_batch = kwargs.get("push_batch", "")
        self.pushed_at = kwargs.get("pushed_at")
        self.status = kwargs.get("status", "sent")  # sent, failed

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "news_id": self.news_id,
            "telegram_message_id": self.telegram_message_id,
            "week_key": self.week_key,
            "push_batch": self.push_batch,
            "pushed_at": self.pushed_at or datetime.now(timezone.utc),
            "status": self.status,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "TelegramPushLog":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)


class PushLogRepository:
    """Repository for Telegram push logs."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize push log repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_telegram_push_log

    def save(self, log: TelegramPushLog) -> Optional[str]:
        """Save a push log entry.

        Args:
            log: TelegramPushLog object

        Returns:
            Document ID if saved
        """
        try:
            doc_ref = self.client.collection(self.collection_name).document()
            doc_ref.set(log.to_dict())
            logger.debug(f"Logged push for news: {log.news_id}")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Error saving push log: {e}")
            return None

    def was_pushed(self, news_id: str, week_key: Optional[str] = None) -> bool:
        """Check if article was already pushed this week.

        Args:
            news_id: News document ID
            week_key: Week key (uses current week if not provided)

        Returns:
            True if already pushed
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
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking push status: {e}")
            return False

    def get_pushed_news_ids(self, week_key: Optional[str] = None) -> Set[str]:
        """Get all news IDs pushed this week.

        Args:
            week_key: Week key (uses current week if not provided)

        Returns:
            Set of news IDs
        """
        if week_key is None:
            week_key = get_week_key()

        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", week_key)
                .get()
            )

            return {doc.to_dict().get("news_id") for doc in docs if doc.to_dict().get("news_id")}

        except Exception as e:
            logger.error(f"Error fetching pushed news IDs: {e}")
            return set()
