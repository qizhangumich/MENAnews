#!/usr/bin/env python3
"""
Telegram bot with inline keyboards for article selection.
"""
import logging
from typing import Optional
from datetime import datetime, timezone

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from tg_bot.keyboards import SelectionKeyboards, CallbackParser
from tg_bot.formatter import TelegramFormatter
from tg_bot.push_service import PushService
from storage.raw_news_repository import RawNewsRepository
from storage.score_repository import ScoreRepository
from storage.selection_repository import NewsSelection, SelectionRepository, get_week_key
from storage.push_log_repository import TelegramPushLog, PushLogRepository
from storage.report_repository import WeeklyReport, ReportRepository
from config import Config

logger = logging.getLogger(__name__)


class MENANewsBot:
    """Telegram bot for MENA news daily review and selection."""

    def __init__(self, config: Config = None):
        """Initialize bot.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.formatter = TelegramFormatter()
        self.parser = CallbackParser()

        # Repositories
        self.news_repo = RawNewsRepository(config=self.config)
        self.score_repo = ScoreRepository(config=self.config)
        self.selection_repo = SelectionRepository(config=self.config)
        self.push_log_repo = PushLogRepository(config=self.config)
        self.report_repo = ReportRepository(config=self.config)

        # Push service
        self.push_service = PushService(
            bot_token=self.config.telegram.bot_token,
            chat_id=self.config.telegram.chat_id,
        )

    def build_application(self) -> Application:
        """Build Telegram application.

        Returns:
            Application instance
        """
        app = Application.builder().token(self.config.telegram.bot_token).build()

        # Command handlers
        app.add_handler(CommandHandler("start", self.cmd_start))
        app.add_handler(CommandHandler("help", self.cmd_help))
        app.add_handler(CommandHandler("status", self.cmd_status))
        app.add_handler(CommandHandler("generate_weekly_report", self.cmd_generate_weekly))

        # Callback query handler
        app.add_handler(CallbackQueryHandler(self.handle_callback))

        return app

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command.

        Args:
            update: Update object
            context: Context object
        """
        welcome_message = """👋 欢迎使用MENA新闻智能系统

本系统用于每日新闻回顾和周报生成。

📋 命令列表:
/start - 显示欢迎信息
/help - 显示帮助信息
/status - 查看本周选文统计
/generate_weekly_report - 生成本周周报

📌 每日推送:
系统会推送候选文章，您可以使用按钮选择分类:
  • 选四 / 选四⭐ - 归入"募资市场动态"
  • 选五 / 选五⭐ - 归入"投资者关注"
  • 四五都选 - 同时归入两个分类
  • 忽略 - 跳过此文章

您的选择将用于生成每周报告。
"""
        await update.message.reply_text(welcome_message)

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command.

        Args:
            update: Update object
            context: Context object
        """
        help_message = """📖 MENA新闻智能系统帮助

【日报流程】
1. 系统每日推送候选新闻
2. 您使用按钮选择分类和重要性
3. 选择结果自动保存

【周报生成】
1. 周五或使用命令手动生成
2. 包含四个分类: 四、五、九
3. 自动发送到邮箱

【分类说明】
• 四 - 募资市场动态 (IPO、融资、并购等)
• 五 - 投资者关注 (SWF、主权基金动向等)
• 九 - 募资的思考和反思 (战略总结)

【问题反馈】
如遇到问题，请联系管理员。
"""
        await update.message.reply_text(help_message)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command.

        Args:
            update: Update object
            context: Context object
        """
        week_key = get_week_key()
        selections = self.selection_repo.get_week_selections(week_key)

        section_4_count = len([s for s in selections if "4" in s.selected_sections])
        section_5_count = len([s for s in selections if "5" in s.selected_sections])
        starred_count = len([s for s in selections if s.starred])

        status_message = f"""📊 本周选文统计 ({week_key})

总选文数: {len(selections)}
  • 分类四 (募资市场): {section_4_count}
  • 分类五 (投资者关注): {section_5_count}
  • 标星文章: {starred_count}

本周已选择 {len(selections)} 篇文章用于周报生成。
"""
        await update.message.reply_text(status_message)

    async def cmd_generate_weekly(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate_weekly_report command.

        Args:
            update: Update object
            context: Context object
        """
        await update.message.reply_text("🔄 正在生成周报，请稍候...")

        # Import here to avoid circular dependency
        from reports.weekly_generator import WeeklyReportGenerator

        generator = WeeklyReportGenerator(config=self.config)
        report = generator.generate()

        if report:
            await update.message.reply_text(
                f"✅ 周报生成成功!\n\n"
                f"📅 周期: {report.week_key}\n"
                f"📧 将发送到: {", ".join(self.config.email.email_recipients)}"
            )
        else:
            await update.message.reply_text("❌ 周报生成失败，请查看日志。")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button presses.

        Args:
            update: Update object
            context: Context object
        """
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        if not callback_data:
            return

        # Parse callback
        if callback_data.startswith("sel|"):
            await self._handle_selection(query, callback_data)
        elif callback_data.startswith("weekly|"):
            await self._handle_weekly_action(query, callback_data)

    async def _handle_selection(self, query, callback_data: str):
        """Handle article selection callback.

        Args:
            query: Callback query
            callback_data: Callback data string
        """
        parsed = self.parser.parse_selection_callback(callback_data)
        if not parsed:
            await query.edit_message_text("❌ 无效的选择")
            return

        news_id = parsed["news_id"]
        sections = parsed["sections"]
        starred = parsed["starred"]

        # Get article and score
        article = self.news_repo.get_by_id(news_id)
        score = self.score_repo.get_by_news_id(news_id)

        if not article:
            await query.edit_message_text("❌ 文章未找到")
            return

        # Save selection
        week_key = get_week_key()
        selection = NewsSelection(
            news_id=news_id,
            title=article.title,
            url=article.url,
            source=article.source,
            week_key=week_key,
            selected_sections=sections,
            starred=starred,
            selection_score=100 if sections else 0,
            selected_at=datetime.now(timezone.utc),
            selected_by="user",
            selection_method="telegram",
        )

        self.selection_repo.save(selection)

        # Update score if selected
        if sections:
            self.score_repo.update_selection_score(news_id, selection_score=100)

        # Format confirmation
        action = parsed["action"]
        confirmation = self.formatter.format_selection_confirmation(
            action=action,
            sections=sections,
            starred=starred,
        )

        # Remove keyboard and show confirmation
        await query.edit_message_text(
            text=f"{query.message.text}\n\n{confirmation}",
            parse_mode="Markdown",
        )

    async def _handle_weekly_action(self, query, callback_data: str):
        """Handle weekly report action callback.

        Args:
            query: Callback query
            callback_data: Callback data string
        """
        parsed = self.parser.parse_weekly_callback(callback_data)
        if not parsed:
            return

        action = parsed["action"]

        if action == "generate":
            await query.edit_message_text("🔄 正在生成周报...")

            from reports.weekly_generator import WeeklyReportGenerator

            generator = WeeklyReportGenerator(config=self.config)
            report = generator.generate()

            if report:
                await query.edit_message_text(
                    f"✅ 周报生成成功!\n\n"
                    f"📅 周期: {report.week_key}\n"
                    f"📧 已发送到: {", ".join(self.config.email.email_recipients)}"
                )
            else:
                await query.edit_message_text("❌ 周报生成失败")

    def run(self):
        """Run the bot (blocking)."""
        app = self.build_application()
        app.run_polling()


def run_bot():
    """Run bot for testing."""
    import logging

    logging.basicConfig(level=logging.INFO)

    bot = MENANewsBot()
    bot.run()
