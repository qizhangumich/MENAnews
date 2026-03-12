#!/usr/bin/env python3
"""
Scoring rules for relevance and importance.
"""
from dataclasses import dataclass
from typing import Set, List


@dataclass
class ScoringRules:
    """Scoring rules configuration."""

    # SWF entities (case-insensitive)
    SWF_ENTITIES: Set[str] = None

    # Relevance keywords and their weights
    RELEVANCE_KEYWORDS: dict = None

    # Event keywords and their weights
    EVENT_KEYWORDS: dict = None

    # Source credibility weights
    SOURCE_WEIGHTS: dict = None

    # Major banks for entity detection
    MAJOR_BANKS: Set[str] = None

    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.SWF_ENTITIES is None:
            self.SWF_ENTITIES = {
                "mubadala", "adia", "adq", "qia", "pif", "kia", "oia",
                "abu dhabi investment authority", "abu dhabi developmental holding company",
                "public investment fund", "qatar investment authority", "kuwait investment authority",
                "oman investment authority", "2pointzero", "2point0",
            }

        if self.RELEVANCE_KEYWORDS is None:
            self.RELEVANCE_KEYWORDS = {
                # Highest priority - Sovereign Wealth Fund related
                "sovereign wealth": 45, "sovereign wealth fund": 45,
                # SWF entities (handled separately with +45 in engine)
                # Core investment activities - HIGHEST
                "investment": 35, "invest": 35, "financing": 30,
                "buyout": 30, "takeover": 30,
                # Family offices (lower priority)
                "family office": 15,
                # Fund/PE/VC
                "fund": 20, "fundraising": 20, "lp": 20, "gp": 20,
                "private equity": 20, "pe": 20, "venture capital": 20, "vc": 20,
                "asset management": 20, "asset manager": 20,
                # Deals
                "ipo": 18, "initial public offering": 18, "listing": 18,
                "acquisition": 18, "merger": 18, "m&a": 18, "m and a": 18,
                "stake": 18,
                "series a": 15, "series b": 15, "series c": 15,
                "funding round": 15, "investment round": 15,
                "strategic investment": 15,
                # Lower priority
                "bank": 5, "bond": 5, "sukuk": 5, "central bank": 5,
            }

        if self.EVENT_KEYWORDS is None:
            self.EVENT_KEYWORDS = {
                "ipo": 35, "initial public offering": 35, "listing": 35,
                "acquisition": 35, "merger": 35, "buyout": 35, "takeover": 35,
                "funding round": 30, "investment round": 30, "series a": 30, "series b": 30,
                "strategic investment": 30, "private equity investment": 30,
                "stake": 30, "equity stake": 30,
                "launch fund": 28, "new fund": 28, "new vehicle": 28, "fund launch": 28,
                "mandate": 28, "aum": 28, "assets under management": 28,
                "regulation": 25, "sanction": 25, "policy": 25, "regulatory": 25,
                "earnings": 18, "guidance": 18, "rating": 18, "upgrade": 18, "downgrade": 18,
                "partnership": 12, "expansion": 12, "agreement": 12,
            }

        if self.SOURCE_WEIGHTS is None:
            self.SOURCE_WEIGHTS = {
                "reuters": 40,
                "financial times": 38, "ft.com": 38,
                "wall street journal": 38, "wsj": 38,
                "bloomberg": 38,
                "the national": 30,
                "zawya": 28,
                "arabian business": 22, "gulf business": 22, "arab news": 22,
            }

        if self.MAJOR_BANKS is None:
            self.MAJOR_BANKS = {
                "hsbc", "standard chartered", "citibank", "jpmorgan",
                "goldman sachs", "morgan stanley", "bank of america",
            }


# Section suggestion rules
SECTION_4_KEYWORDS = [
    "raise", "raising", "raised", "fundraising", "fundraise", "financing",
    "capital raise", "ipo", "initial public offering", "listing",
    "deal", "acquisition", "merger", "m&a", "buyout",
    "infrastructure investment", "fund launch", "new fund",
]

SECTION_5_KEYWORDS = [
    "qia", "mubadala", "adia", "pif", "adq", "oia", "kia", "2pointzero",
    "sovereign fund", "sovereign wealth fund", "swf", "family office",
    "investor behavior", "capital allocation", "investment strategy",
]
