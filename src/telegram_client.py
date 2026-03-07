#!/usr/bin/env python3
"""
Telegram client module for sending daily digest messages.

Handles communication with Telegram Bot API.
"""

import logging
import requests
from typing import Optional
from datetime import datetime, timezone, timedelta

from .config import get_config

logger = logging.getLogger(__name__)


# Telegram API base URL
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient:
    """Client for sending messages via Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """Initialize Telegram client.

        Args:
            bot_token: Telegram bot token (defaults to config).
            chat_id: Target chat ID (defaults to config).
        """
        config = get_config()
        self.bot_token = bot_token or config.telegram_bot_token
        self.chat_id = chat_id or config.telegram_chat_id

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")

    def _api_call(self, method: str, data: dict) -> dict:
        """Make API call to Telegram.

        Args:
            method: API method name.
            data: Request data.

        Returns:
            API response as dict.
        """
        url = TELEGRAM_API_URL.format(token=self.bot_token, method=method)

        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API error: {result.get('description')}")
                raise Exception(f"Telegram API error: {result.get('description')}")

            return result

        except requests.RequestException as e:
            logger.error(f"Telegram API request failed: {e}")
            raise

    def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False
    ) -> dict:
        """Send a text message.

        Args:
            text: Message text.
            parse_mode: Parse mode (HTML, Markdown, or None).
            disable_web_page_preview: Disable link preview.

        Returns:
            API response.
        """
        # Telegram message length limit is 4096 characters
        MAX_LENGTH = 4096

        if len(text) > MAX_LENGTH:
            # Split into multiple messages
            messages = self._split_message(text, MAX_LENGTH)
            results = []
            for msg in messages:
                result = self._send_single_message(msg, parse_mode, disable_web_page_preview)
                results.append(result)
            return {"ok": True, "result": results}

        return self._send_single_message(text, parse_mode, disable_web_page_preview)

    def _send_single_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False
    ) -> dict:
        """Send a single message.

        Args:
            text: Message text.
            parse_mode: Parse mode.
            disable_web_page_preview: Disable link preview.

        Returns:
            API response.
        """
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }

        if parse_mode:
            data["parse_mode"] = parse_mode

        return self._api_call("sendMessage", data)

    def _split_message(self, text: str, max_length: int) -> list[str]:
        """Split message into chunks.

        Tries to split at paragraph boundaries.

        Args:
            text: Message text.
            max_length: Maximum chunk length.

        Returns:
            List of message chunks.
        """
        chunks = []
        current_chunk = ""

        # Split by double newline (paragraphs)
        paragraphs = text.split("\n\n")

        for paragraph in paragraphs:
            test_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph

            if len(test_chunk) > max_length:
                # Current chunk is full, save it
                if current_chunk:
                    chunks.append(current_chunk)

                # If paragraph itself is too long, split by lines
                if len(paragraph) > max_length:
                    lines = paragraph.split("\n")
                    for line in lines:
                        if len(line) > max_length:
                            # Split long line
                            for i in range(0, len(line), max_length - 10):
                                chunks.append(line[i:i + max_length - 10])
                        else:
                            chunks.append(line)
                    current_chunk = ""
                else:
                    current_chunk = paragraph
            else:
                current_chunk = test_chunk

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


def format_daily_digest(summaries: list, digest_date: datetime) -> str:
    """Format daily digest for Telegram with bilingual summaries.

    Args:
        summaries: List of ArticleSummary objects with bilingual content.
        digest_date: Date for the digest.

    Returns:
        Formatted message text.
    """
    # Format date in GMT+8
    tz = timezone(timedelta(hours=8))
    date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

    # Header
    lines = [
        f"📰 <b>MENA Investment Daily｜过去24小时Top{len(summaries)}</b>",
        f"📅 {date_str}",
        "",
    ]

    # Articles with bilingual summaries
    for i, summary in enumerate(summaries, 1):
        # Get effective published time
        published_at = summary.published_at
        if published_at:
            time_str = published_at.astimezone(tz).strftime("%m-%d %H:%M")
        else:
            time_str = "未知时间"

        # Full title (no truncation)
        title_en = summary.title_en.strip()
        title_cn = summary.title_cn.strip()

        # URL
        url = summary.url if summary.url != "#" else "无链接"

        lines.extend([
            f"<b>{i}. {title_en}</b>",
            f"<b>{title_cn}</b>",
            "",
            f"📌 <b>Key Message (CN):</b> {summary.summary_cn}",
            f"📌 <b>Key Message (EN):</b> {summary.summary_en}",
            "",
            f"🏷️ {summary.tags} | 📰 {summary.source} | 🕒 {time_str}",
            f"🔗 {url}",
            "",
        ])

    return "\n".join(lines)


def send_daily_digest(summaries: list, digest_date: datetime) -> bool:
    """Send daily digest to Telegram with bilingual summaries.

    Args:
        summaries: List of ArticleSummary objects with bilingual content.
        digest_date: Date for the digest.

    Returns:
        True if successful.
    """
    try:
        client = TelegramClient()
        message = format_daily_digest(summaries, digest_date)
        client.send_message(message)
        logger.info(f"Daily digest sent with {len(summaries)} articles")
        return True

    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}")
        return False
