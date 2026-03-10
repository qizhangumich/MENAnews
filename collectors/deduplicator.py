#!/usr/bin/env python3
"""
Deduplication utility for news articles.
"""
import logging
import hashlib
from typing import List, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ArticleDeduplicator:
    """Deduplicates articles by URL and title."""

    def __init__(self):
        """Initialize deduplicator."""
        self.seen_urls: Set[str] = set()
        self.seen_hashes: Set[str] = set()

    def normalize_url(self, url: str) -> str:
        """Normalize URL for comparison.

        Args:
            url: Original URL

        Returns:
            Normalized URL
        """
        if not url:
            return ""

        # Remove protocol
        url = url.lower()
        url = url.replace("https://", "").replace("http://", "").replace("www.", "")

        # Remove tracking parameters
        url = url.split("?")[0]

        # Remove trailing slash
        url = url.rstrip("/")

        return url

    def normalize_title(self, title: str) -> str:
        """Normalize title for comparison.

        Args:
            title: Original title

        Returns:
            Normalized title
        """
        if not title:
            return ""

        # Convert to lowercase
        title = title.lower()

        # Remove special characters
        title = "".join(c if c.isalnum() or c.isspace() else " " for c in title)

        # Normalize whitespace
        title = " ".join(title.split())

        return title

    def generate_hash(self, article: dict) -> str:
        """Generate hash for article.

        Args:
            article: Article dictionary

        Returns:
            Hash string
        """
        url = article.get("url", "")
        title = article.get("title", "")[:100]

        content = f"{self.normalize_url(url)}|{self.normalize_title(title)}"
        return hashlib.md5(content.encode()).hexdigest()

    def deduplicate(self, articles: List[dict]) -> List[dict]:
        """Remove duplicate articles.

        Args:
            articles: List of article dictionaries

        Returns:
            Deduplicated list
        """
        unique_articles = []

        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "")

            # Check by URL
            normalized_url = self.normalize_url(url)
            if normalized_url in self.seen_urls:
                logger.debug(f"Duplicate by URL: {title[:50]}")
                continue

            # Check by hash
            article_hash = self.generate_hash(article)
            if article_hash in self.seen_hashes:
                logger.debug(f"Duplicate by hash: {title[:50]}")
                continue

            # Add to seen sets
            self.seen_urls.add(normalized_url)
            self.seen_hashes.add(article_hash)

            unique_articles.append(article)

        removed = len(articles) - len(unique_articles)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate articles")

        return unique_articles

    def deduplicate_by_list(self, articles: List[dict], existing_urls: Set[str]) -> List[dict]:
        """Remove articles that already exist in database.

        Args:
            articles: List of new article dictionaries
            existing_urls: Set of existing URLs

        Returns:
            Filtered list
        """
        new_articles = []

        for article in articles:
            url = article.get("url", "")
            normalized_url = self.normalize_url(url)

            if normalized_url not in existing_urls:
                new_articles.append(article)
            else:
                logger.debug(f"Skipping existing article: {article.get('title', '')[:50]}")

        return new_articles
