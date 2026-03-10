#!/usr/bin/env python3
"""
Feed registry for managing RSS feed configurations.
"""
import logging
import json
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)


class FeedRegistry:
    """Registry for RSS feed sources."""

    def __init__(self, config_path: str = None):
        """Initialize feed registry.

        Args:
            config_path: Path to RSS sources JSON file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "rss_sources.json"

        self.config_path = Path(config_path)
        self._sources = None

    @property
    def sources(self) -> List[Dict]:
        """Get all feed sources.

        Returns:
            List of source dictionaries
        """
        if self._sources is None:
            self._load_sources()
        return self._sources

    def _load_sources(self):
        """Load sources from configuration file."""
        try:
            if not self.config_path.exists():
                logger.warning(f"RSS sources file not found: {self.config_path}")
                self._sources = self._get_default_sources()
                return

            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._sources = data.get("sources", [])

            logger.info(f"Loaded {len(self._sources)} RSS sources")

        except Exception as e:
            logger.error(f"Error loading RSS sources: {e}")
            self._sources = self._get_default_sources()

    def _get_default_sources(self) -> List[Dict]:
        """Get default RSS sources when config file is missing.

        Returns:
            List of default source dictionaries
        """
        return [
            {"name": "Reuters Middle East", "url": "https://www.reuters.com/world/middle-east/rss"},
            {"name": "Reuters Business", "url": "https://www.reuters.com/business/rss"},
            {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss"},
            {"name": "The National", "url": "https://www.thenationalnews.com/rss"},
        ]

    def get_by_name(self, name: str) -> Dict:
        """Get feed source by name.

        Args:
            name: Source name

        Returns:
            Source dictionary or None
        """
        for source in self.sources:
            if source.get("name") == name:
                return source
        return None

    def get_urls(self) -> List[str]:
        """Get all feed URLs.

        Returns:
            List of URLs
        """
        return [s.get("url", "") for s in self.sources if s.get("url")]


# Singleton instance
_registry = None


def get_registry() -> FeedRegistry:
    """Get global feed registry instance.

    Returns:
        FeedRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = FeedRegistry()
    return _registry


# Legacy compatibility for rss_sources.py
def get_rss_sources() -> List[Dict]:
    """Get RSS sources (legacy function).

    Returns:
        List of source dictionaries
    """
    return get_registry().sources
