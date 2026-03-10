#!/usr/bin/env python3
"""
Scoring engine for computing article relevance and importance.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from scoring.rules import ScoringRules, SECTION_4_KEYWORDS, SECTION_5_KEYWORDS
from storage.raw_news_repository import RawNews
from storage.score_repository import NewsScore
from config import Config

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Engine for scoring news articles."""

    def __init__(self, config: Config = None, rules: ScoringRules = None):
        """Initialize scoring engine.

        Args:
            config: Configuration object
            rules: Scoring rules (uses default if not provided)
        """
        self.config = config or Config()
        self.rules = rules or ScoringRules()

    def score_article(self, article: RawNews) -> NewsScore:
        """Compute all scores for an article.

        Args:
            article: RawNews object to score

        Returns:
            NewsScore object with computed scores
        """
        # Get text content
        text = f"{article.title} {article.snippet_text or article.description}".lower()

        # Compute scores
        relevance = self._compute_relevance_score(text, article)
        importance = self._compute_importance_score(text, article)

        # Calculate total machine score
        total_machine = (
            self.config.score_weights.relevance_weight * relevance +
            self.config.score_weights.importance_weight * importance
        )

        # Generate tags
        entity_tags, topic_tags = self._generate_tags(text, article.source)

        # Suggest sections
        section_suggested = self._suggest_sections(text)

        return NewsScore(
            news_id=article.id if hasattr(article, 'id') else "",
            relevance_score=relevance,
            importance_score=importance,
            selection_score=self.config.score_weights.selection_score_default,
            total_machine_score=total_machine,
            final_priority_score=total_machine,
            section_suggested=section_suggested,
            entity_tags=list(entity_tags),
            topic_tags=list(topic_tags),
            scored_at=datetime.now(timezone.utc),
            score_version="1.0",
        )

    def _compute_relevance_score(self, text: str, article: RawNews) -> float:
        """Compute relevance score based on content keywords.

        Args:
            text: Lowercase text content
            article: RawNews object

        Returns:
            Relevance score (0-100)
        """
        score = 0.0

        # Check for SWF entities (highest weight)
        swf_found = False
        for entity in self.rules.SWF_ENTITIES:
            if entity in text:
                score += 45
                swf_found = True
                logger.debug(f"SWF entity match: {entity}")
                break

        # If no SWF entity, check for sovereign wealth/SWF
        if not swf_found:
            if "sovereign wealth" in text or " swf " in text or " swf." in text:
                score += 35

        # Check for family office
        if "family office" in text:
            score += 30

        # Check relevance keywords
        for keyword, weight in self.rules.RELEVANCE_KEYWORDS.items():
            if keyword in text:
                score += weight

        return min(score, 100.0)

    def _compute_importance_score(self, text: str, article: RawNews) -> float:
        """Compute importance score based on source and impact.

        Args:
            text: Lowercase text content
            article: RawNews object

        Returns:
            Importance score (0-100)
        """
        # Source weight
        source_weight = self._compute_source_weight(article.source)

        # Event weight
        event_weight = self._compute_event_weight(text)

        # Entity weight
        entity_weight = self._compute_entity_weight(text)

        # Freshness weight
        freshness_weight = self._compute_freshness_weight(article)

        total = source_weight + event_weight + entity_weight + freshness_weight
        return min(total, 100.0)

    def _compute_source_weight(self, source: str) -> int:
        """Compute source credibility weight.

        Args:
            source: Source name

        Returns:
            Source weight score
        """
        if not source:
            return 15

        source_lower = source.lower()
        for name, weight in self.rules.SOURCE_WEIGHTS.items():
            if name in source_lower:
                return weight

        return 15

    def _compute_event_weight(self, text: str) -> int:
        """Compute event impact weight.

        Args:
            text: Lowercase text content

        Returns:
            Event weight score
        """
        max_weight = 0
        for keyword, weight in self.rules.EVENT_KEYWORDS.items():
            if keyword in text:
                max_weight = max(max_weight, weight)
        return max_weight

    def _compute_entity_weight(self, text: str) -> int:
        """Compute entity importance weight.

        Args:
            text: Lowercase text content

        Returns:
            Entity weight score
        """
        # SWF entities
        for entity in self.rules.SWF_ENTITIES:
            if entity in text:
                return 20

        # Major banks
        for bank in self.rules.MAJOR_BANKS:
            if bank in text:
                return 12

        # Regulator/central bank
        if any(x in text for x in ["central bank", "regulator", "sec", "sca"]):
            return 10

        return 0

    def _compute_freshness_weight(self, article: RawNews) -> int:
        """Compute freshness weight based on article age.

        Args:
            article: RawNews object

        Returns:
            Freshness weight score
        """
        effective_time = article.published_at or article.fetched_at
        if not effective_time:
            return 1

        now = datetime.now(timezone.utc)
        hours_ago = (now - effective_time.replace(tzinfo=timezone.utc)).total_seconds() / 3600

        if hours_ago < 6:
            return 5
        elif hours_ago < 12:
            return 4
        elif hours_ago < 24:
            return 3
        elif hours_ago < 48:
            return 2
        else:
            return 1

    def _generate_tags(self, text: str, source: str) -> tuple[set, set]:
        """Generate entity and topic tags.

        Args:
            text: Lowercase text content
            source: Article source

        Returns:
            Tuple of (entity_tags, topic_tags)
        """
        entity_tags = set()
        topic_tags = set()

        # Check for SWF
        for entity in self.rules.SWF_ENTITIES:
            if entity in text:
                entity_tags.add("SWF")
                break

        # Check for specific entity tags
        if "family office" in text:
            entity_tags.add("Family Office")

        # Check for specific topic tags
        if any(kw in text for kw in ["ipo", "listing", "initial public offering"]):
            topic_tags.add("IPO")

        if any(kw in text for kw in ["acquisition", "merger", "m&a", "buyout"]):
            topic_tags.add("M&A")

        if any(kw in text for kw in ["fund", "fundraising", "funding round"]):
            topic_tags.add("Fundraising")

        if any(kw in text for kw in ["regulation", "policy", "sanction"]):
            topic_tags.add("Policy")

        return entity_tags, topic_tags

    def _suggest_sections(self, text: str) -> List[str]:
        """Suggest which report sections this article belongs to.

        Args:
            text: Lowercase text content

        Returns:
            List of section numbers (["4"], ["5"], or ["4", "5"])
        """
        sections = []

        # Check for section 4 keywords (fundraising/market dynamics)
        if any(kw in text for kw in SECTION_4_KEYWORDS):
            sections.append("4")

        # Check for section 5 keywords (investor focus)
        if any(kw in text for kw in SECTION_5_KEYWORDS):
            sections.append("5")

        return sections

    def score_batch(self, articles: List[RawNews]) -> List[NewsScore]:
        """Score multiple articles.

        Args:
            articles: List of RawNews objects

        Returns:
            List of NewsScore objects
        """
        scores = []
        for article in articles:
            score = self.score_article(article)
            scores.append(score)
        return scores
