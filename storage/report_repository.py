#!/usr/bin/env python3
"""
Weekly report repository for storing generated reports.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from google.cloud import firestore
from storage.firestore_client import FirestoreClient
from config import Config
from storage.selection_repository import get_week_key

logger = logging.getLogger(__name__)


class WeeklyReport:
    """Weekly report data model."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")  # Firestore document ID
        self.week_key = kwargs.get("week_key", get_week_key())
        self.section_4 = kwargs.get("section_4", "")  # 募资市场动态
        self.section_5 = kwargs.get("section_5", "")  # 投资者关注
        self.section_9 = kwargs.get("section_9", "")  # 募资的思考和反思
        self.selected_news_ids = kwargs.get("selected_news_ids", [])
        self.generated_at = kwargs.get("generated_at")
        self.status = kwargs.get("status", "draft")  # draft, final
        self.email_sent = kwargs.get("email_sent", False)
        self.email_sent_at = kwargs.get("email_sent_at")
        self.email_to = kwargs.get("email_to", "")

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "week_key": self.week_key,
            "section_4": self.section_4,
            "section_5": self.section_5,
            "section_9": self.section_9,
            "selected_news_ids": self.selected_news_ids,
            "generated_at": self.generated_at or datetime.now(timezone.utc),
            "status": self.status,
            "email_sent": self.email_sent,
            "email_sent_at": self.email_sent_at,
            "email_to": self.email_to,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "WeeklyReport":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)


class ReportRepository:
    """Repository for weekly reports."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize report repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_weekly_reports

    def save(self, report: WeeklyReport) -> Optional[str]:
        """Save or update a weekly report.

        Args:
            report: WeeklyReport object

        Returns:
            Document ID if saved
        """
        try:
            # Check if report exists for this week
            existing = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", report.week_key)
                .limit(1)
                .get()
            )

            if existing:
                doc_id = list(existing)[0].id
                self.client.collection(self.collection_name).document(doc_id).set(report.to_dict())
                logger.info(f"Updated weekly report: {report.week_key}")
                return doc_id
            else:
                doc_ref = self.client.collection(self.collection_name).document()
                doc_ref.set(report.to_dict())
                logger.info(f"Saved weekly report: {report.week_key}")
                return doc_ref.id

        except Exception as e:
            logger.error(f"Error saving weekly report: {e}")
            return None

    def get_by_week(self, week_key: str) -> Optional[WeeklyReport]:
        """Get report by week key.

        Args:
            week_key: Week key (YYYY-Www format)

        Returns:
            WeeklyReport object or None
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", week_key)
                .limit(1)
                .get()
            )

            if docs:
                doc = list(docs)[0]
                data = doc.to_dict()
                return WeeklyReport(id=doc.id, **data)
            return None

        except Exception as e:
            logger.error(f"Error fetching weekly report: {e}")
            return None

    def mark_email_sent(self, week_key: str, email_to: str) -> bool:
        """Mark report as emailed.

        Args:
            week_key: Week key
            email_to: Recipient email

        Returns:
            True if updated
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("week_key", "==", week_key)
                .limit(1)
                .get()
            )

            if docs:
                doc_id = list(docs)[0].id
                self.client.collection(self.collection_name).document(doc_id).update(
                    {
                        "email_sent": True,
                        "email_sent_at": datetime.now(timezone.utc),
                        "email_to": email_to,
                    }
                )
                logger.info(f"Marked report {week_key} as emailed to {email_to}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error marking email sent: {e}")
            return False
