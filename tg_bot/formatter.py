#!/usr/bin/env python3
"""
Message formatter for Telegram messages.
"""
from datetime import datetime, timezone, timedelta
from telegram.constants import ParseMode

from storage.raw_news_repository import RawNews
from storage.score_repository import NewsScore


class TelegramFormatter:
    """Format news articles for Telegram messages."""

    def __init__(self, timezone_offset: int = 8):
        """Initialize formatter.

        Args:
            timezone_offset: Timezone offset in hours (default: GMT+8)
        """
        self.tz = timezone(timedelta(hours=timezone_offset))

    def format_article_message(
        self,
        article: RawNews,
        score: NewsScore,
        index: int = None,
        chinese_translation: str = None,
    ) -> str:
        """Format an article for Telegram daily review.

        Args:
            article: RawNews object
            score: NewsScore object
            index: Optional article number
            chinese_translation: Optional Chinese translation

        Returns:
            Formatted message string
        """
        # Article number
        prefix = f"{index}. " if index else ""

        # Use Chinese translation if available, otherwise use English title
        title = chinese_translation or article.title or "无标题"

        # URL
        url = article.url or "无链接"

        # Simple format: number + chinese title + link (no markdown)
        message = f"{prefix}{title}\n\n🔗 {url}"

        return message

    def _format_date(self, date: datetime) -> str:
        """Format date for display.

        Args:
            date: datetime object

        Returns:
            Formatted date string
        """
        if not date:
            return "未知时间"

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(self.tz).strftime("%m-%d %H:%M")

    def _format_tags(self, score: NewsScore) -> str:
        """Format tags for display.

        Args:
            score: NewsScore object

        Returns:
            Formatted tags string
        """
        tags = []

        if score.entity_tags:
            tags.extend([f"🏷️ {tag}" for tag in score.entity_tags])

        if score.topic_tags:
            tags.extend([f"📌 {tag}" for tag in score.topic_tags])

        return " | ".join(tags) if tags else "📰 新闻"

    def _format_section_hint(self, sections: list) -> str:
        """Format section suggestion hint.

        Args:
            sections: List of section numbers

        Returns:
            Formatted hint string
        """
        if not sections:
            return "💡 建议分类: 无"

        section_names = {"4": "四", "5": "五"}
        names = [section_names.get(s, s) for s in sections]
        return f"💡 建议分类: {'/'.join(names)}"

    def _format_snippet(self, text: str) -> str:
        """Format article snippet.

        Args:
            text: Raw text

        Returns:
            Formatted snippet
        """
        if not text:
            return "无摘要"

        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Limit length
        if len(text) > 300:
            text = text[:297] + "..."

        return text

    def format_selection_confirmation(
        self,
        action: str,
        sections: list = None,
        starred: bool = False,
    ) -> str:
        """Format selection confirmation message.

        Args:
            action: Action performed
            sections: Selected sections
            starred: Whether article was starred

        Returns:
            Confirmation message
        """
        if sections:
            section_names = {"4": "四", "5": "五"}
            names = [section_names.get(s, s) for s in sections]

            if starred:
                return f"✅ 已加入{'/'.join(names)}并标星"
            else:
                return f"✅ 已加入{'/'.join(names)}"
        else:
            return "🗑️ 已忽略"

    def format_weekly_summary(self, selections_count: int, week_key: str) -> str:
        """Format weekly selection summary.

        Args:
            selections_count: Number of selected articles
            week_key: Week key

        Returns:
            Summary message
        """
        return f"""📊 本周选文统计 ({week_key})

共选中 {selections_count} 篇文章
"""
