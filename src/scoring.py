#!/usr/bin/env python3
"""
Scoring module for computing relevance and importance scores.

Implements the scoring system for MENA news articles.
"""

import re
import logging
from typing import List, Optional, Set, Tuple
from datetime import datetime, timezone

from .firestore_client import NewsArticle
from .config import get_config

logger = logging.getLogger(__name__)


# SWF entity list (case-insensitive)
SWF_ENTITIES: Set[str] = {
    "mubadala", "adia", "adq", "qia", "pif", "kia", "oia",
    "abu dhabi investment authority", "abu dhabi developmental holding company",
    "public investment fund", "qatar investment authority", "kuwait investment authority",
    "oman investment authority"
}

# Topic keywords for relevance scoring
RELEVANCE_KEYWORDS: dict[str, int] = {
    # High weight - SWF entities (handled separately)
    # Medium weight
    "family office": 30,
    # Fund/investment related
    "fund": 20, "fundraising": 20, "lp": 20, "gp": 20,
    "private equity": 20, "pe": 20, "venture capital": 20, "vc": 20,
    "asset management": 20, "asset manager": 20,
    # Deal terms
    "ipo": 15, "initial public offering": 15, "listing": 15,
    "acquisition": 15, "merger": 15, "m&a": 15, "m and a": 15,
    "stake": 15, "buyout": 15, "takeover": 15,
    "series a": 15, "series b": 15, "series c": 15,
    "funding round": 15, "investment round": 15,
    "strategic investment": 15,
    # Investment/financing
    "investment": 10, "invest": 10, "financing": 10, "finance": 10,
    # Finance words (low base)
    "bank": 5, "bond": 5, "sukuk": 5, "central bank": 5,
}

# Event keywords for importance scoring
EVENT_KEYWORDS: dict[str, int] = {
    # High impact
    "ipo": 35, "initial public offering": 35, "listing": 35,
    "acquisition": 35, "merger": 35, "buyout": 35, "takeover": 35,
    # Funding
    "funding round": 30, "investment round": 30, "series a": 30, "series b": 30,
    "strategic investment": 30, "private equity investment": 30,
    "stake": 30, "equity stake": 30,
    # Fund launch
    "launch fund": 28, "new fund": 28, "new vehicle": 28, "fund launch": 28,
    "mandate": 28, "aum": 28, "assets under management": 28,
    # Policy/regulation
    "regulation": 25, "sanction": 25, "policy": 25, "regulatory": 25,
    # Earnings
    "earnings": 18, "guidance": 18, "rating": 18, "upgrade": 18, "downgrade": 18,
    # Generic
    "partnership": 12, "expansion": 12, "agreement": 12,
    "lifestyle": 5, "transport": 5, "travel": 5,
}

# Source weights
SOURCE_WEIGHTS: dict[str, int] = {
    "reuters": 40,
    "financial times": 38, "ft.com": 38,
    "wall street journal": 38, "wsj": 38,
    "bloomberg": 38,
    "the national": 30,
    "zawya": 28,
    "arabian business": 22, "gulf business": 22, "arab news": 22,
}


def compute_relevance_score(article: NewsArticle) -> float:
    """Compute relevance score based on title and snippet.

    Args:
        article: NewsArticle with title and description.

    Returns:
        Relevance score from 0-100.
    """
    text = f"{article.title} {article.description}".lower()
    score = 0.0

    # Check for SWF entities (high weight)
    swf_found = False
    for entity in SWF_ENTITIES:
        if entity in text:
            score += 45
            swf_found = True
            break

    if not swf_found:
        # Check for "sovereign wealth" or "swf"
        if "sovereign wealth" in text or " swf " in text or " swf." in text:
            score += 35

    # Check for family office
    if "family office" in text:
        score += 30

    # Check relevance keywords
    for keyword, weight in RELEVANCE_KEYWORDS.items():
        if keyword in text:
            score += weight

    return min(score, 100.0)


def compute_importance_score(article: NewsArticle) -> float:
    """Compute importance score based on source, event, entity, and freshness.

    Args:
        article: NewsArticle with metadata.

    Returns:
        Importance score from 0-100.
    """
    text = f"{article.title} {article.description}".lower()

    # Source weight
    source_weight = compute_source_weight(article.source)

    # Event weight
    event_weight = compute_event_weight(text)

    # Entity weight
    entity_weight = compute_entity_weight(text)

    # Freshness weight
    freshness_weight = compute_freshness_weight(article)

    total = source_weight + event_weight + entity_weight + freshness_weight
    return min(total, 100.0)


def compute_source_weight(source: str) -> int:
    """Compute source credibility weight."""
    if not source:
        return 15  # Default for unknown sources

    source_lower = source.lower()
    for name, weight in SOURCE_WEIGHTS.items():
        if name in source_lower:
            return weight

    return 15  # Default


def compute_event_weight(text: str) -> int:
    """Compute event impact weight from keywords."""
    max_weight = 0
    for keyword, weight in EVENT_KEYWORDS.items():
        if keyword in text:
            max_weight = max(max_weight, weight)

    return max_weight


def compute_entity_weight(text: str) -> int:
    """Compute entity importance weight."""
    # SWF entities
    for entity in SWF_ENTITIES:
        if entity in text:
            return 20

    # Major banks
    major_banks = ["hsbc", "standard chartered", "citibank", "jpmorgan", "goldman sachs"]
    for bank in major_banks:
        if bank in text:
            return 12

    # Regulator/central bank
    if any(x in text for x in ["central bank", "regulator", "sec", "sca"]):
        return 10

    return 0


def compute_freshness_weight(article: NewsArticle) -> int:
    """Compute freshness weight based on article age."""
    effective_time = article.get_effective_published_time()
    if not effective_time:
        return 1

    now = datetime.now(timezone.utc)
    hours_ago = (now - effective_time).total_seconds() / 3600

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


def compute_total_score(article: NewsArticle) -> float:
    """Compute total score from relevance and importance.

    TotalScore = 0.65 * RelevanceScore + 0.35 * ImportanceScore

    Args:
        article: NewsArticle.

    Returns:
        Total score from 0-100.
    """
    relevance = compute_relevance_score(article)
    importance = compute_importance_score(article)

    return 0.65 * relevance + 0.35 * importance


def generate_tags(article: NewsArticle) -> List[str]:
    """Generate tags for an article.

    Args:
        article: NewsArticle.

    Returns:
        List of tags (max 5).
    """
    text = f"{article.title} {article.description}".lower()
    tags = []

    # Check for SWF
    for entity in SWF_ENTITIES:
        if entity in text:
            tags.append("SWF")
            break

    # Check for specific tags
    if "family office" in text:
        tags.append("Family Office")

    if any(kw in text for kw in ["ipo", "listing", "initial public offering"]):
        tags.append("IPO")

    if any(kw in text for kw in ["acquisition", "merger", "m&a", "buyout"]):
        tags.append("M&A")

    if any(kw in text for kw in ["fund", "fundraising", "funding round", "series a", "series b"]):
        tags.append("Fundraising")

    if any(kw in text for kw in ["regulation", "policy", "sanction"]):
        tags.append("Policy")

    if any(kw in text for kw in ["earnings", "profit", "loss", "revenue"]):
        tags.append("Markets")

    # Limit to 5 tags
    return tags[:5]


def score_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Score all articles and update their fields.

    Args:
        articles: List of NewsArticle objects.

    Returns:
        Same articles with scores populated.
    """
    for article in articles:
        article.relevance_score = compute_relevance_score(article)
        article.importance_score = compute_importance_score(article)
        article.total_score = compute_total_score(article)
        article.tags = generate_tags(article)

    return articles


def filter_and_rank_daily(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Filter and rank articles for daily digest.

    Keeps articles with RelevanceScore >= 25, then takes top 10 by TotalScore.
    If fewer than 10, fills remaining by ImportanceScore.

    Args:
        articles: List of scored NewsArticle objects.

    Returns:
        Top articles for daily digest.
    """
    config = get_config()
    threshold = config.daily_relevance_threshold
    top_n = config.daily_top_n

    # Filter by relevance threshold
    relevant = [a for a in articles if (a.relevance_score or 0) >= threshold]

    # Sort by total score
    relevant.sort(key=lambda a: a.total_score or 0, reverse=True)

    result = relevant[:top_n]

    # If we need more articles, add by importance score
    if len(result) < top_n:
        remaining = [a for a in articles if a not in result]
        # Filter out obvious non-business lifestyle content
        remaining = [
            a for a in remaining
            if not any(kw in f"{a.title} {a.description}".lower() for kw in ["lifestyle", "travel", "fashion", "food"])
        ]
        remaining.sort(key=lambda a: a.importance_score or 0, reverse=True)
        result.extend(remaining[:top_n - len(result)])

    return result[:top_n]


def deduplicate_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Deduplicate articles by normalized title and URL.

    Args:
        articles: List of NewsArticle objects.

    Returns:
        Deduplicated list (keeps first occurrence).
    """
    from .extract import normalize_title, normalize_url

    seen_titles: Set[str] = set()
    seen_urls: Set[str] = set()
    unique = []

    for article in articles:
        # Check by URL
        if article.url:
            norm_url = normalize_url(article.url)
            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

        # Check by normalized title
        if article.title:
            norm_title = normalize_title(article.title)
            if norm_title in seen_titles:
                continue
            seen_titles.add(norm_title)

        unique.append(article)

    return unique
