#!/usr/bin/env python3
"""
Inline keyboard layouts for Telegram bot.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class SelectionKeyboards:
    """Inline keyboard layouts for article selection."""

    @staticmethod
    def get_selection_keyboard(news_id: str) -> InlineKeyboardMarkup:
        """Create selection keyboard for an article.

        Args:
            news_id: News document ID

        Returns:
            Inline keyboard markup
        """
        keyboard = [
            [
                InlineKeyboardButton("4️⃣ 选四", callback_data=f"sel|4|{news_id}"),
                InlineKeyboardButton("5️⃣ 选五", callback_data=f"sel|5|{news_id}"),
            ],
            [
                InlineKeyboardButton("⭐ 四", callback_data=f"sel|4s|{news_id}"),
                InlineKeyboardButton("⭐ 五", callback_data=f"sel|5s|{news_id}"),
            ],
            [
                InlineKeyboardButton("📋 两篇都选", callback_data=f"sel|45|{news_id}"),
                InlineKeyboardButton("🗑️ 忽略", callback_data=f"sel|x|{news_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_weekly_keyboard() -> InlineKeyboardMarkup:
        """Create keyboard for weekly report actions.

        Returns:
            Inline keyboard markup
        """
        keyboard = [
            [
                InlineKeyboardButton("生成周报", callback_data="weekly|generate"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)


class CallbackParser:
    """Parser for Telegram callback data."""

    @staticmethod
    def parse_selection_callback(callback_data: str) -> dict:
        """Parse selection callback data.

        Args:
            callback_data: Callback data string (e.g., "sel|4|newsId")

        Returns:
            Dictionary with parsed data or None if invalid
        """
        parts = callback_data.split("|")
        if len(parts) != 3 or parts[0] != "sel":
            return None

        action = parts[1]
        news_id = parts[2]

        # Parse action
        sections = []
        starred = False

        if action == "4":
            sections = ["4"]
        elif action == "4s":
            sections = ["4"]
            starred = True
        elif action == "5":
            sections = ["5"]
        elif action == "5s":
            sections = ["5"]
            starred = True
        elif action == "45":
            sections = ["4", "5"]
        elif action == "x":
            sections = []  # Ignored

        return {
            "action": action,
            "news_id": news_id,
            "sections": sections,
            "starred": starred,
        }

    @staticmethod
    def parse_weekly_callback(callback_data: str) -> dict:
        """Parse weekly report callback data.

        Args:
            callback_data: Callback data string

        Returns:
            Dictionary with parsed data or None if invalid
        """
        parts = callback_data.split("|")
        if len(parts) < 2 or parts[0] != "weekly":
            return None

        return {
            "action": parts[1],
        }


# Callback data format constants
CALLBACK_SELECTION = "sel"
CALLBACK_WEEKLY = "weekly"

ACTION_SELECT_4 = "4"
ACTION_SELECT_4_STAR = "4s"
ACTION_SELECT_5 = "5"
ACTION_SELECT_5_STAR = "5s"
ACTION_SELECT_BOTH = "45"
ACTION_IGNORE = "x"
ACTION_WEEKLY_GENERATE = "generate"
