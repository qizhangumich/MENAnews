#!/usr/bin/env python3
"""
Topic clustering module for grouping related articles.

Implements topic-based clustering without embeddings.
"""

import re
import logging
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from .firestore_client import NewsArticle
from .scoring import SWF_ENTITIES

logger = logging.getLogger(__name__)


# Event type keywords
EVENT_TYPE_KEYWORDS: dict[str, set[str]] = {
    "IPO": {"ipo", "initial public offering", "listing", "market debut", "public listing"},
    "M&A": {"acquisition", "merger", "buyout", "takeover", "m&a", "m and a"},
    "Funding": {"funding round", "investment round", "series a", "series b", "series c", "financing"},
    "FundLaunch": {"launch fund", "new fund", "fund launch", "new vehicle", "new investment vehicle"},
    "Policy": {"regulation", "policy", "regulatory", "sanction", "law", "legislation"},
    "Markets": {"earnings", "profit", "loss", "revenue", "stock", "share", "trading", "index", "bond", "sukuk"},
}


@dataclass
class Topic:
    """Represents a clustered topic."""

    topic_key: str
    entity: Optional[str]
    event_type: str
    top_keyword: str
    articles: List[NewsArticle] = field(default_factory=list)

    @property
    def topic_score(self) -> float:
        """Sum of TotalScore for all articles in topic."""
        return sum(a.total_score or 0 for a in self.articles)

    @property
    def source_diversity(self) -> int:
        """Number of distinct sources."""
        sources = {a.source.lower().strip() for a in self.articles if a.source}
        return len(sources)

    @property
    def source_diversity_bonus(self) -> int:
        """Bonus based on source diversity."""
        if self.source_diversity >= 3:
            return 10
        elif self.source_diversity >= 2:
            return 5
        return 0

    @property
    def volume_bonus(self) -> int:
        """Bonus based on article count."""
        return min(10, len(self.articles))

    @property
    def total_topic_score(self) -> float:
        """Total topic score including bonuses."""
        return self.topic_score + self.source_diversity_bonus + self.volume_bonus


def determine_event_type(text: str) -> str:
    """Determine event type from text.

    Args:
        text: Lowercased text to analyze.

    Returns:
        Event type string (IPO, M&A, Funding, FundLaunch, Policy, Markets, Other).
    """
    text = text.lower()

    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return event_type

    return "Other"


def determine_top_entity(text: str) -> Optional[str]:
    """Determine top SWF entity from text.

    Args:
        text: Lowercased text to analyze.

    Returns:
        Entity name or None.
    """
    text = text.lower()

    # Check in order of specificity
    entity_names = {
        "mubadala": "Mubadala",
        "abu dhabi investment authority": "ADIA",
        "abu dhabi developmental holding": "ADQ",
        "public investment fund": "PIF",
        "qatar investment authority": "QIA",
        "kuwait investment authority": "KIA",
        "oman investment authority": "OIA",
    }

    for entity_key, entity_name in entity_names.items():
        if entity_key in text:
            return entity_name

    return None


def extract_top_keyword(text: str) -> str:
    """Extract the strongest matched keyword for topic labeling.

    Args:
        text: Lowercased text to analyze.

    Returns:
        Top keyword string.
    """
    text = text.lower()

    # Priority keywords (higher importance first)
    priority_keywords = [
        "ipo", "initial public offering", "listing",
        "acquisition", "merger", "buyout", "takeover",
        "funding round", "series a", "series b", "series c",
        "fund launch", "new fund",
        "sovereign wealth", "family office",
        "private equity", "venture capital",
        "regulation", "policy", "sanction",
        "earnings", "profit", "revenue",
        "rate", "bond", "sukuk", "central bank",
    ]

    for keyword in priority_keywords:
        if keyword in text:
            return keyword

    # Fallback: extract first significant noun/phrase
    words = text.split()
    significant_words = [
        w for w in words
        if len(w) > 3 and w.isalpha()
    ]

    if significant_words:
        return significant_words[0]

    return "General"


def build_topic_key(article: NewsArticle) -> str:
    """Build topic key for clustering.

    Format: (top_entity or "General") | event_type | top_keyword

    Args:
        article: NewsArticle.

    Returns:
        Topic key string.
    """
    text = f"{article.title} {article.description}".lower()

    entity = determine_top_entity(text) or "General"
    event_type = determine_event_type(text)
    top_keyword = extract_top_keyword(text)

    return f"{entity} | {event_type} | {top_keyword}"


def cluster_articles_by_topic(articles: List[NewsArticle]) -> List[Topic]:
    """Cluster articles by topic.

    Args:
        articles: List of scored NewsArticle objects.

    Returns:
        List of Topic objects sorted by total_topic_score.
    """
    # Group by topic key
    topic_groups: Dict[str, List[NewsArticle]] = defaultdict(list)

    for article in articles:
        topic_key = build_topic_key(article)
        topic_groups[topic_key].append(article)

    # Create Topic objects
    topics = []
    for topic_key, grouped_articles in topic_groups.items():
        # Extract components from topic_key
        parts = topic_key.split(" | ")
        if len(parts) >= 3:
            entity = parts[0] if parts[0] != "General" else None
            event_type = parts[1]
            top_keyword = parts[2]
        else:
            entity = None
            event_type = "Other"
            top_keyword = topic_key

        # Sort articles by total score
        grouped_articles.sort(key=lambda a: a.total_score or 0, reverse=True)

        topic = Topic(
            topic_key=topic_key,
            entity=entity,
            event_type=event_type,
            top_keyword=top_keyword,
            articles=grouped_articles
        )
        topics.append(topic)

    # Sort by total topic score
    topics.sort(key=lambda t: t.total_topic_score, reverse=True)

    logger.info(f"Created {len(topics)} topic clusters from {len(articles)} articles")
    return topics


def get_top_topics(topics: List[Topic], n: int = 10) -> List[Topic]:
    """Get top N topics by score.

    Args:
        topics: List of Topic objects.
        n: Number of topics to return.

    Returns:
        Top N topics.
    """
    return topics[:n]


def format_topic_title(topic: Topic) -> str:
    """Format topic title for display in Chinese.

    Args:
        topic: Topic object.

    Returns:
        Formatted Chinese title.
    """
    entity_map = {
        "Mubadala": "穆巴达拉",
        "ADIA": "阿布扎比投资局",
        "ADQ": "阿布扎比发展控股公司",
        "PIF": "沙特公共投资基金",
        "QIA": "卡塔尔投资局",
        "KIA": "科威特投资局",
        "OIA": "阿曼投资局",
    }

    event_type_map = {
        "IPO": "IPO/上市",
        "M&A": "并购/M&A",
        "Funding": "融资",
        "FundLaunch": "基金设立",
        "Policy": "政策监管",
        "Markets": "市场动态",
        "Other": "其他",
    }

    entity_str = entity_map.get(topic.entity, topic.entity) if topic.entity else "综合"
    event_str = event_type_map.get(topic.event_type, topic.event_type)

    return f"{entity_str} - {event_str}"


def summarize_topic(topic: Topic, max_articles: int = 5) -> Dict[str, any]:
    """Summarize a topic for weekly digest.

    Args:
        topic: Topic object.
        max_articles: Maximum number of articles to include.

    Returns:
        Dictionary with topic summary.
    """
    # Get top articles by total score
    top_articles = topic.articles[:max_articles]

    # Generate key developments
    developments = []
    for article in top_articles[:3]:
        developments.append({
            "title": article.title,
            "source": article.source,
            "url": article.url,
            "score": article.total_score,
        })

    return {
        "topic_key": topic.topic_key,
        "title": format_topic_title(topic),
        "entity": topic.entity,
        "event_type": topic.event_type,
        "top_keyword": topic.top_keyword,
        "topic_score": topic.topic_score,
        "source_diversity": topic.source_diversity,
        "article_count": len(topic.articles),
        "developments": developments,
        "top_articles": top_articles,
    }
