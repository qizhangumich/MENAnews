#!/usr/bin/env python3
"""
Extraction module for processing HTML descriptions.

Handles URL extraction and text cleaning from HTML snippets.
"""

import re
import logging
from typing import Optional
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class LinkExtractor(HTMLParser):
    """HTML parser to extract links."""

    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "a":
            for attr_name, attr_value in attrs:
                if attr_name == "href" and attr_value:
                    self.links.append(attr_value)

    def get_links(self) -> list[str]:
        return self.links


def extract_first_article_url(description_html: str) -> Optional[str]:
    """Extract the first article URL from HTML description.

    Chooses the first link that is NOT the site homepage.

    Args:
        description_html: HTML snippet containing <a href="..."> tags.

    Returns:
        First non-homepage URL, or None if not found.
    """
    if not description_html:
        return None

    try:
        parser = LinkExtractor()
        parser.feed(description_html)
        links = parser.get_links()

        for url in links:
            url = url.strip()
            if not url:
                continue

            try:
                parsed = urlparse(url)

                # Skip empty URLs or non-http(s)
                if not parsed.scheme or parsed.scheme not in ("http", "https"):
                    continue

                # Skip if it looks like a homepage (no path or just "/")
                path = parsed.path.strip("/")
                if not path:
                    # This is likely a homepage
                    continue

                # Skip common non-article patterns
                if any(x in path.lower() for x in ["author", "tag", "category", "search"]):
                    continue

                # Valid article URL
                return url

            except Exception as e:
                logger.debug(f"Error parsing URL {url}: {e}")
                continue

        return None

    except Exception as e:
        logger.warning(f"Error extracting URL from HTML: {e}")
        return None


class TextExtractor(HTMLParser):
    """HTML parser to extract text content."""

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.in_script = False
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style"):
            self.in_script = True

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style"):
            self.in_script = False

    def handle_data(self, data: str) -> None:
        if not self.in_script and not self.in_style:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


def html_to_text(description_html: str, min_length: int = 600, max_length: int = 900) -> str:
    """Convert HTML description to plain text snippet.

    Strips tags, collapses whitespace, and truncates to desired length.

    Args:
        description_html: HTML snippet.
        min_length: Minimum desired length (will try to achieve this).
        max_length: Maximum length of output.

    Returns:
        Plain text snippet.
    """
    if not description_html:
        return ""

    try:
        # Remove script and style content first
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', description_html, flags=re.DOTALL | re.IGNORECASE)

        # Extract text
        parser = TextExtractor()
        parser.feed(cleaned)
        text = parser.get_text()

        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Truncate to max length
        if len(text) > max_length:
            # Try to find a good break point (sentence end)
            truncated = text[:max_length]
            last_period = truncated.rfind('.')
            last_space = truncated.rfind(' ')

            if last_period > max_length * 0.7:
                text = truncated[:last_period + 1]
            elif last_space > max_length * 0.8:
                text = truncated[:last_space] + "..."

        return text

    except Exception as e:
        logger.warning(f"Error converting HTML to text: {e}")
        # Fallback: simple regex strip
        text = re.sub(r'<[^>]+>', '', description_html)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_length] if text else ""


def normalize_title(title: str) -> str:
    """Normalize title for deduplication.

    Converts to lowercase and removes punctuation.

    Args:
        title: Original title.

    Returns:
        Normalized title.
    """
    if not title:
        return ""

    # Convert to lowercase
    normalized = title.lower()

    # Remove common punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)

    # Collapse whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication.

    Removes common tracking parameters and standardizes format.

    Args:
        url: Original URL.

    Returns:
        Normalized URL.
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)

        # Remove common tracking parameters
        # (simplified - a full implementation would use urllib.parse)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path,
            '',  # Remove params
            '',  # Remove query (for simplicity)
            ''   # Remove fragment
        ))

        # Remove trailing slash
        if normalized.endswith('/'):
            normalized = normalized[:-1]

        return normalized

    except Exception:
        return url.lower().strip()
