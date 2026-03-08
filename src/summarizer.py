#!/usr/bin/env python3
"""
OpenAI summarizer module for generating bilingual news summaries.

Uses OpenAI API to generate Chinese and English summaries of MENA news articles.
"""

import logging
import os
from typing import Optional
from dataclasses import dataclass

from .firestore_client import NewsArticle
from .config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ArticleSummary:
    """Bilingual summary of a news article."""
    article: NewsArticle
    title_cn: str
    summary_cn: str
    title_en: str
    summary_en: str
    tags: str

    @property
    def url(self) -> str:
        return self.article.url or "#"

    @property
    def source(self) -> str:
        return self.article.source or "Unknown"

    @property
    def published_at(self):
        return self.article.published_at or self.article.fetched_at

    def to_html(self, index: int) -> str:
        """Format as HTML for email."""
        url = self.url
        source = self.source
        published_at = self.published_at
        time_str = published_at.strftime("%Y-%m-%d %H:%M") if published_at else "N/A"

        return f"""
        <div class="article">
            <h4>{index}. {self.title_cn}</h4>
            <p class="subtitle">{self.title_en}</p>
            <p class="summary-cn"><strong>中文摘要：</strong>{self.summary_cn}</p>
            <p class="summary-en"><strong>English Summary：</strong>{self.summary_en}</p>
            <p class="meta">
                🏷️ 标签：{self.tags} |
                📰 来源：{source} |
                🕒 时间：{time_str} |
                <a href="{url}">阅读原文</a>
            </p>
        </div>
"""

    def to_text(self, index: int) -> str:
        """Format as plain text."""
        url = self.url
        source = self.source
        published_at = self.published_at
        time_str = published_at.strftime("%Y-%m-%d %H:%M") if published_at else "N/A"

        return f"""
{index}. {self.title_cn}
   {self.title_en}

   中文摘要：{self.summary_cn}
   English Summary：{self.summary_en}

   标签：{self.tags} | 来源：{source} | 时间：{time_str}
   链接：{url}
"""


class OpenAISummarizer:
    """Summarizer using OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the summarizer.

        Args:
            api_key: OpenAI API key (defaults to config).
        """
        config = get_config()
        self.api_key = api_key or config.openai_api_key
        self.model = config.openai_model

        if not self.api_key:
            logger.warning("OpenAI API key not configured. Summaries will be rule-based.")
            self.enabled = False
        else:
            self.enabled = True

    def summarize_article(self, article: NewsArticle) -> ArticleSummary:
        """Generate bilingual summary for an article.

        Args:
            article: NewsArticle to summarize.

        Returns:
            ArticleSummary with Chinese and English content.
        """
        if not self.enabled:
            logger.warning("OpenAI not enabled, using rule-based fallback")
            return self._rule_based_summary(article)

        logger.info(f"Using OpenAI to translate: '{article.title[:50]}...'")

        try:
            import openai

            # Prepare content
            title = article.title or ""
            description = article.description or ""
            # Strip HTML from description
            if "<" in description:
                import re
                description = re.sub(r'<[^>]+>', ' ', description)
                description = re.sub(r'\s+', ' ', description).strip()

            content = f"Title: {title}\n\nDescription: {description}"

            # Generate summary using OpenAI
            prompt = f"""You are a bilingual news editor specializing in Middle East business and investment news.

Please analyze the following news article and provide a bilingual summary:

{content}

Provide your response in the following JSON format:
{{
  "title_cn": "Chinese translation of the title (keep it concise and professional)",
  "summary_cn": "2-3 sentence Chinese summary focusing on business/investment implications for GCC and SWF readers",
  "title_en": "Original English title (or improved version)",
  "summary_en": "2-3 sentence English summary focusing on business/investment implications",
  "tags": "2-3 relevant tags in Chinese (e.g., 主权基金, IPO, 并购, 沙特, 阿联酋)"
}}

Return ONLY the JSON, no other text."""

            response = openai.OpenAI(api_key=self.api_key).chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a bilingual business news editor specializing in Middle East markets. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            import json
            content = response.choices[0].message.content.strip()

            # Try to extract JSON from response (in case there's extra text)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)

            # Validate required fields
            if not result.get("title_cn"):
                raise ValueError("Missing title_cn in OpenAI response")

            return ArticleSummary(
                article=article,
                title_cn=result.get("title_cn", title),
                summary_cn=result.get("summary_cn", ""),
                title_en=result.get("title_en", title),
                summary_en=result.get("summary_en", ""),
                tags=result.get("tags", "新闻")
            )

        except Exception as e:
            logger.error(f"OpenAI summarization failed for article '{article.title[:50]}...': {type(e).__name__}: {e}")
            return self._rule_based_summary(article)

    def summarize_articles_batch(self, articles: list) -> list[ArticleSummary]:
        """Summarize multiple articles with progress tracking.

        Args:
            articles: List of NewsArticle objects.

        Returns:
            List of ArticleSummary objects.
        """
        summaries = []

        for i, article in enumerate(articles, 1):
            logger.info(f"Summarizing article {i}/{len(articles)}: {article.title[:50]}...")
            summary = self.summarize_article(article)
            summaries.append(summary)

        return summaries

    def _rule_based_summary(self, article: NewsArticle) -> ArticleSummary:
        """Generate a rule-based summary without OpenAI.

        Args:
            article: NewsArticle to summarize.

        Returns:
            ArticleSummary with basic translation.
        """
        title = article.title or ""
        description = article.description or ""

        # Strip HTML
        if "<" in description:
            import re
            description = re.sub(r'<[^>]+>', ' ', description)
            description = re.sub(r'\s+', ' ', description).strip()

        # Truncate description
        description_text = description[:300] + "..." if len(description) > 300 else description

        # Basic title translation (rule-based)
        title_cn = self._translate_title(title)
        summary_cn = f"{title_cn}。{description_text[:200]}..."

        # Generate tags from content
        content_lower = f"{title} {description}".lower()
        tags = []
        if "ipo" in content_lower or "listing" in content_lower:
            tags.append("IPO")
        if "m&a" in content_lower or "acquisition" in content_lower or "merger" in content_lower:
            tags.append("并购")
        if "fund" in content_lower or "investment" in content_lower:
            tags.append("投资")
        if "saudi" in content_lower or "ksa" in content_lower:
            tags.append("沙特")
        if "uae" in content_lower or "abu dhabi" in content_lower or "dubai" in content_lower:
            tags.append("阿联酋")
        if "qatar" in content_lower:
            tags.append("卡塔尔")

        if not tags:
            tags.append("新闻")

        return ArticleSummary(
            article=article,
            title_cn=title_cn,
            summary_cn=summary_cn,
            title_en=title,
            summary_en=description_text,
            tags=" | ".join(tags[:3])
        )

    def _translate_title(self, title: str) -> str:
        """Basic rule-based title translation.

        Args:
            title: English title.

        Returns:
            Chinese title (basic translation).
        """
        # Basic keyword substitutions
        translations = {
            "Saudi Arabia": "沙特阿拉伯",
            "UAE": "阿联酋",
            "Abu Dhabi": "阿布扎比",
            "Dubai": "迪拜",
            "Qatar": "卡塔尔",
            "Kuwait": "科威特",
            "Oman": "阿曼",
            "Bahrain": "巴林",
            "IPO": "IPO",
            "M&A": "并购",
            "sovereign wealth fund": "主权基金",
            "fund": "基金",
            "investment": "投资",
            "acquisition": "收购",
            "merger": "合并",
            "oil": "石油",
            "gas": "天然气",
            "central bank": "央行",
        }

        result = title
        for en, cn in translations.items():
            result = result.replace(en, cn)

        return result
