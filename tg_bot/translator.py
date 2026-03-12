#!/usr/bin/env python3
"""
Simple translator for daily Telegram push.
Uses cheap LLM model for Chinese translation.
"""
import logging
from typing import Optional

from config import Config
from storage.raw_news_repository import RawNews

logger = logging.getLogger(__name__)


class DailyTranslator:
    """Translate articles to Chinese for daily push."""

    def __init__(self, config: Config = None):
        """Initialize translator.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self._client = None

    @property
    def client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self.config.llm.api_key)
        return self._client

    def translate_article(self, article: RawNews, max_length: int = 150) -> str:
        """Translate article to Chinese (short version for daily push).

        Args:
            article: RawNews object
            max_length: Maximum length of translation

        Returns:
            Chinese translation or original title if failed
        """
        try:
            title = article.title or "无标题"
            description = (article.snippet_text or article.description or "")[:500]

            # Use cheaper model for daily push
            model = self.config.llm.daily_model

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个新闻翻译助手。将英文新闻翻译成简洁的中文摘要（50-100字），重点翻译关键信息（公司、金额、事件）。"
                    },
                    {
                        "role": "user",
                        "content": f"请翻译以下新闻（50-100字）：\n\n标题: {title}\n内容: {description}"
                    }
                ],
                temperature=0.3,
                max_tokens=200,
            )

            translation = response.choices[0].message.content.strip()
            return translation[:max_length]

        except Exception as e:
            logger.error(f"Translation error: {e}")
            return article.title or "无标题"

    def translate_title_only(self, title: str, max_length: int = 80) -> str:
        """Translate just the title to Chinese.

        Args:
            title: Article title
            max_length: Maximum length

        Returns:
            Chinese translation or original title if failed
        """
        try:
            model = self.config.llm.daily_model

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "将英文新闻标题翻译成简洁的中文（30字以内）。"
                    },
                    {
                        "role": "user",
                        "content": f"翻译标题: {title}"
                    }
                ],
                temperature=0.3,
                max_tokens=80,
            )

            translation = response.choices[0].message.content.strip()
            return translation[:max_length]

        except Exception as e:
            logger.error(f"Title translation error: {e}")
            return title[:max_length]
