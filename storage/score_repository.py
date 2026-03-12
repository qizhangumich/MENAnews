#!/usr/bin/env python3
"""
Score repository for storing article scores.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from google.cloud import firestore
from storage.firestore_client import FirestoreClient
from config import Config

logger = logging.getLogger(__name__)


class NewsScore:
    """News score data model."""

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "")  # Firestore document ID
        self.news_id = kwargs.get("news_id", "")
        self.relevance_score = kwargs.get("relevance_score", 0.0)
        self.importance_score = kwargs.get("importance_score", 0.0)
        self.selection_score = kwargs.get("selection_score", 0)
        self.total_machine_score = kwargs.get("total_machine_score", 0.0)
        self.final_priority_score = kwargs.get("final_priority_score", 0.0)
        self.section_suggested = kwargs.get("section_suggested", [])
        self.entity_tags = kwargs.get("entity_tags", [])
        self.topic_tags = kwargs.get("topic_tags", [])
        self.scored_at = kwargs.get("scored_at")
        self.score_version = kwargs.get("score_version", "1.0")

    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore."""
        return {
            "news_id": self.news_id,
            "relevance_score": self.relevance_score,
            "importance_score": self.importance_score,
            "selection_score": self.selection_score,
            "total_machine_score": self.total_machine_score,
            "final_priority_score": self.final_priority_score,
            "section_suggested": self.section_suggested,
            "entity_tags": self.entity_tags,
            "topic_tags": self.topic_tags,
            "scored_at": self.scored_at or datetime.now(timezone.utc),
            "score_version": self.score_version,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "NewsScore":
        """Create from Firestore document."""
        return cls(id=doc_id, **data)


class ScoreRepository:
    """Repository for news scores."""

    def __init__(self, client: Optional[FirestoreClient] = None, config: Optional[Config] = None):
        """Initialize score repository.

        Args:
            client: Firestore client (creates new if not provided)
            config: Configuration object
        """
        self.config = config or Config()
        self.client = client or FirestoreClient(self.config)
        self.collection_name = self.config.collection_news_scores

    def save(self, score: NewsScore) -> Optional[str]:
        """Save or update a score record.

        Args:
            score: NewsScore object

        Returns:
            Document ID if saved
        """
        try:
            # Check if score exists for this news_id
            existing = (
                self.client.collection(self.collection_name)
                .where("news_id", "==", score.news_id)
                .limit(1)
                .get()
            )

            if existing:
                doc_id = list(existing)[0].id
                self.client.collection(self.collection_name).document(doc_id).set(score.to_dict())
                logger.debug(f"Updated score for news: {score.news_id}")
                return doc_id
            else:
                doc_ref = self.client.collection(self.collection_name).document()
                doc_ref.set(score.to_dict())
                logger.debug(f"Saved score for news: {score.news_id}")
                return doc_ref.id

        except Exception as e:
            logger.error(f"Error saving score: {e}")
            return None

    def get_by_news_id(self, news_id: str) -> Optional[NewsScore]:
        """Get score by news ID.

        Args:
            news_id: Raw news document ID

        Returns:
            NewsScore object or None
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("news_id", "==", news_id)
                .limit(1)
                .get()
            )

            if docs:
                doc = list(docs)[0]
                data = doc.to_dict()
                return NewsScore(id=doc.id, **data)
            return None

        except Exception as e:
            logger.error(f"Error fetching score for {news_id}: {e}")
            return None

    def get_recent_candidates(
        self, hours_back: int = 24, min_score: float = 25.0, limit: int = 100
    ) -> List[NewsScore]:
        """Get recent high-scoring articles for daily push.

        Args:
            hours_back: Hours to look back
            min_score: Minimum total machine score
            limit: Maximum number of articles

        Returns:
            List of NewsScore objects
        """
        from datetime import timedelta

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        try:
            # Get recent scores without limit (filter in memory)
            # Use a large limit to ensure we get all recent articles
            docs = (
                self.client.collection(self.collection_name)
                .where("scored_at", ">=", cutoff_time)
                .order_by("scored_at", direction="DESCENDING")
                .limit(limit * 5)  # Increased limit to get more candidates
                .get()
            )

            scores = []
            for doc in docs:
                data = doc.to_dict()
                score = NewsScore(id=doc.id, **data)
                if score.total_machine_score >= min_score:
                    scores.append(score)
                if len(scores) >= limit:
                    break

            # Sort by final priority score (highest first)
            scores.sort(key=lambda s: s.final_priority_score or s.total_machine_score, reverse=True)

            logger.info(f"Found {len(scores)} candidates (score >= {min_score})")
            return scores

        except Exception as e:
            logger.error(f"Error fetching candidates: {e}")
            return []

    def get_top_scores(self, limit: int = 30, week_key: str = None, min_relevance: float = 20.0) -> List[NewsScore]:
        """Get top scored articles for weekly report.

        Args:
            limit: Maximum number of articles to return
            week_key: Optional week key filter
            min_relevance: Minimum relevance score threshold (default 20.0)

        Returns:
            List of NewsScore objects sorted by final_priority_score
        """
        from datetime import timedelta

        # Get articles from the past 7 days if no week_key specified
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)

        try:
            # Get scores from the past week
            docs = (
                self.client.collection(self.collection_name)
                .where("scored_at", ">=", cutoff_time)
                .limit(limit * 3)  # Get more to filter by relevance
                .get()
            )

            scores = []
            for doc in docs:
                data = doc.to_dict()
                score = NewsScore(id=doc.id, **data)
                # Filter by minimum relevance score
                if score.relevance_score and score.relevance_score >= min_relevance:
                    scores.append(score)
                if len(scores) >= limit * 2:
                    break

            # Sort by final priority score and take top N
            scores.sort(key=lambda s: s.final_priority_score or s.total_machine_score or 0, reverse=True)

            logger.info(f"Found {len(scores[:limit])} top scores (min_relevance={min_relevance}) for weekly report")
            return scores[:limit]

        except Exception as e:
            logger.error(f"Error fetching top scores: {e}")
            return []

    def update_selection_score(self, news_id: str, selection_score: int = 100) -> bool:
        """Update selection score for human-selected articles.

        Args:
            news_id: Raw news document ID
            selection_score: Selection score (default 100)

        Returns:
            True if updated
        """
        try:
            docs = (
                self.client.collection(self.collection_name)
                .where("news_id", "==", news_id)
                .limit(1)
                .get()
            )

            if docs:
                doc_id = list(docs)[0].id
                self.client.collection(self.collection_name).document(doc_id).update(
                    {
                        "selection_score": selection_score,
                        "final_priority_score": selection_score,
                    }
                )
                logger.info(f"Updated selection score for {news_id}: {selection_score}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating selection score: {e}")
            return False
