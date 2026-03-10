#!/usr/bin/env python3
"""
RSS feed parser for extracting news articles.
"""
import logging
import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any
from html import unescape
import re

logger = logging.getLogger(__name__)


class RSSFeedParser:
    """Parser for RSS feeds."""

    def __init__(self):
        """Initialize RSS parser."""
        self.user_agent = "MENA-News-Collector/1.0"

    def parse_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Parse an RSS feed and extract articles.

        Args:
            feed_url: URL of the RSS feed

        Returns:
            List of article dictionaries
        """
        try:
            feed = feedparser.parse(feed_url)

            if not feed.entries:
                logger.warning(f"No entries found in feed: {feed_url}")
                return []

            articles = []
            for entry in feed.entries:
                article = self._parse_entry(entry)
                if article:
                    articles.append(article)

            logger.info(f"Parsed {len(articles)} articles from {feed_url}")
            return articles

        except Exception as e:
            logger.error(f"Error parsing feed {feed_url}: {e}")
            return []

    def _parse_entry(self, entry: Any) -> Dict[str, Any]:
        """Parse a single RSS entry.

        Args:
            entry: Feedparser entry object

        Returns:
            Article dictionary or None
        """
        try:
            # Extract title
            title = self._clean_text(entry.get("title", ""))

            # Extract URL
            url = entry.get("link", "")
            if not url:
                logger.debug("Entry has no URL, skipping")
                return None

            # Extract description
            description = entry.get("description", "")
            description = self._clean_html(description)

            # Extract snippet (plain text version)
            snippet = self._html_to_text(description)

            # Extract published date
            published_at = self._extract_date(entry)

            return {
                "title": title,
                "url": url,
                "description": description,
                "snippet_text": snippet,
                "published_at": published_at,
            }

        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text.

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        if not text:
            return ""
        return unescape(text).strip()

    def _clean_html(self, html: str) -> str:
        """Clean HTML while preserving basic structure.

        Args:
            html: Raw HTML string

        Returns:
            Cleaned HTML
        """
        if not html:
            return ""

        # Remove script tags, style tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)

        return html.strip()

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text.

        Args:
            html: HTML string

        Returns:
            Plain text
        """
        if not html:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Decode HTML entities
        text = unescape(text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_date(self, entry: Any) -> datetime:
        """Extract and parse published date.

        Args:
            entry: Feedparser entry

        Returns:
            datetime object or None
        """
        # Try published_parsed first
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        # Try updated_parsed
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass

        return None
