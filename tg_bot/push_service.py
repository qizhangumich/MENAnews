#!/usr/bin/env python3
"""
Push service for sending daily Telegram messages.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from telegram import Bot
from telegram.error import TelegramError

from tg_bot.keyboards import SelectionKeyboards
from tg_bot.formatter import TelegramFormatter
from storage.raw_news_repository import RawNewsRepository
from storage.score_repository import NewsScore
from storage.push_log_repository import TelegramPushLog, PushLogRepository
from storage.selection_repository import get_week_key
from config import Config

logger = logging.getLogger(__name__)


class PushService:
    """Service for pushing articles to Telegram."""

    def __init__(self, bot_token: str = None, chat_id: str = None, config: Config = None):
        """Initialize push service.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            config: Configuration object
        """
        self.config = config or Config()
        self.bot_token = bot_token or self.config.telegram.bot_token
        self.chat_id = chat_id or self.config.telegram.chat_id
        self.formatter = TelegramFormatter()

        self.bot = Bot(token=self.bot_token)
        self.push_log_repo = PushLogRepository(config=self.config)

    async def send_daily_digest(
        self,
        articles: List,
        scores: List[NewsScore],
        batch_id: str = None,
    ) -> dict:
        """Send daily digest to Telegram.

        Args:
            articles: List of RawNews objects
            scores: List of NewsScore objects
            batch_id: Optional batch identifier

        Returns:
            Statistics dictionary
        """
        stats = {
            "sent": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": datetime.now(timezone.utc),
        }

        week_key = get_week_key()

        # Create lookup for scores
        score_map = {s.news_id: s for s in scores}

        for i, article in enumerate(articles, 1):
            try:
                # Check if already pushed
                if self.push_log_repo.was_pushed(article.id, week_key):
                    stats["skipped"] += 1
                    continue

                # Get score
                score = score_map.get(article.id)
                if not score:
                    logger.warning(f"No score found for article {article.id}")
                    stats["skipped"] += 1
                    continue

                # Format message
                message = self.formatter.format_article_message(article, score, index=i)

                # Create keyboard
                keyboard = SelectionKeyboards.get_selection_keyboard(article.id)

                # Send message
                msg = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

                # Log push
                push_log = TelegramPushLog(
                    news_id=article.id,
                    telegram_message_id=msg.message_id,
                    week_key=week_key,
                    push_batch=batch_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M"),
                    status="sent",
                )
                self.push_log_repo.save(push_log)

                stats["sent"] += 1
                logger.info(f"Sent article {i}: {article.title[:50]}")

                # Small delay between messages
                import asyncio
                await asyncio.sleep(0.5)

            except TelegramError as e:
                logger.error(f"Telegram error sending article {article.id}: {e}")
                stats["failed"] += 1

            except Exception as e:
                logger.error(f"Error sending article {article.id}: {e}")
                stats["failed"] += 1

        stats["duration_seconds"] = (datetime.now(timezone.utc) - stats["start_time"]).total_seconds()

        logger.info(f"Daily digest sent: {stats['sent']} sent, {stats['failed']} failed, {stats['skipped']} skipped")

        return stats

    def send_daily_digest_sync(
        self,
        articles: List,
        scores: List[NewsScore],
        batch_id: str = None,
    ) -> dict:
        """Send daily digest synchronously.

        Args:
            articles: List of RawNews objects
            scores: List of NewsScore objects
            batch_id: Optional batch identifier

        Returns:
            Statistics dictionary
        """
        import asyncio

        return asyncio.run(self.send_daily_digest(articles, scores, batch_id))

    async def send_message(self, text: str, keyboard: Optional[SelectionKeyboards] = None) -> bool:
        """Send a simple message to Telegram.

        Args:
            text: Message text
            keyboard: Optional inline keyboard

        Returns:
            True if successful
        """
        try:
            reply_markup = keyboard.get_selection_keyboard("dummy") if keyboard else None

            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                reply_markup=reply_markup,
            )
            return True

        except TelegramError as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_message_sync(self, text: str, keyboard: Optional[SelectionKeyboards] = None) -> bool:
        """Send a simple message synchronously.

        Args:
            text: Message text
            keyboard: Optional inline keyboard

        Returns:
            True if successful
        """
        import asyncio

        return asyncio.run(self.send_message(text, keyboard))
