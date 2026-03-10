#!/usr/bin/env python3
"""
Weekly report generator for sections 四, 五, 九.
Generates Chinese reports from selected articles.
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from storage.selection_repository import SelectionRepository, get_week_key
from storage.raw_news_repository import RawNewsRepository
from storage.report_repository import WeeklyReport, ReportRepository
from email.sender import EmailSender
from config import Config
from config import Config

logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """Generate weekly reports from selected articles."""

    def __init__(self, config: Config = None):
        """Initialize generator.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.selection_repo = SelectionRepository(config=self.config)
        self.news_repo = RawNewsRepository(config=self.config)
        self.report_repo = ReportRepository(config=self.config)
        self.email_sender = EmailSender(config=self.config)

    def generate(self, week_key: str = None) -> Optional[WeeklyReport]:
        """Generate weekly report.

        Args:
            week_key: Week key (uses current week if not provided)

        Returns:
            WeeklyReport object or None if failed
        """
        if week_key is None:
            week_key = get_week_key()

        logger.info(f"Generating weekly report for {week_key}")

        # Get selections for the week
        selections = self.selection_repo.get_week_selections(week_key)

        if not selections:
            logger.warning(f"No selections found for week {week_key}")
            return None

        logger.info(f"Found {len(selections)} selections")

        # Group by section
        section_4_selections = [s for s in selections if "4" in s.selected_sections]
        section_5_selections = [s for s in selections if "5" in s.selected_sections]

        # Generate sections
        section_4_content = self._generate_section_4(section_4_selections)
        section_5_content = self._generate_section_5(section_5_selections)
        section_9_content = self._generate_section_9(selections, week_key)

        # Create report
        report = WeeklyReport(
            week_key=week_key,
            section_4=section_4_content,
            section_5=section_5_content,
            section_9=section_9_content,
            selected_news_ids=[s.news_id for s in selections],
            generated_at=datetime.now(timezone.utc),
            status="final",
            email_to=self.config.email.email_to,
        )

        # Save report
        report_id = self.report_repo.save(report)
        if report_id:
            logger.info(f"Saved report: {report_id}")

        # Send email
        if self.email_sender.send_weekly_report(report):
            self.report_repo.mark_email_sent(week_key, self.config.email.email_to)
            logger.info("Weekly report sent successfully")
        else:
            logger.error("Failed to send weekly report email")

        return report

    def _generate_section_4(self, selections: List) -> str:
        """Generate section 四: 募资市场动态.

        Args:
            selections: List of NewsSelection objects

        Returns:
            Formatted section content
        """
        if not selections:
            return "本周暂无募资市场动态。"

        content = f"四. 募资市场动态\n\n"

        # Sort by starred status and time
        selections_sorted = sorted(
            selections,
            key=lambda s: (not s.starred, s.selected_at or datetime.min),
            reverse=True,
        )

        # Group by themes
        ipo_deals = []
        fund_raisings = []
        mna_deals = []
        other = []

        for selection in selections_sorted[:20]:  # Top 20
            article = self.news_repo.get_by_id(selection.news_id)
            if not article:
                continue

            title = article.title
            source = article.source
            url = article.url

            star = "⭐ " if selection.starred else ""
            item = f"{star}• {title}\n  来源: {source}\n"

            text = (title + " " + (article.description or "")).lower()

            if any(kw in text for kw in ["ipo", "listing", "initial public offering"]):
                ipo_deals.append(item)
            elif any(kw in text for kw in ["acquisition", "merger", "m&a", "buyout"]):
                mna_deals.append(item)
            elif any(kw in text for kw in ["fund", "funding", "fundraising", "raising"]):
                fund_raisings.append(item)
            else:
                other.append(item)

        # Build section
        section_num = 1

        if ipo_deals:
            content += f"{section_num}. IPO与上市动态\n\n"
            for item in ipo_deals[:5]:
                content += item + "\n"
            content += "\n"
            section_num += 1

        if fund_raisings:
            content += f"{section_num}. 融资动态\n\n"
            for item in fund_raisings[:5]:
                content += item + "\n"
            content += "\n"
            section_num += 1

        if mna_deals:
            content += f"{section_num}. 并购活动\n\n"
            for item in mna_deals[:5]:
                content += item + "\n"
            content += "\n"
            section_num += 1

        if other:
            content += f"{section_num}. 其他市场动态\n\n"
            for item in other[:5]:
                content += item + "\n"

        return content

    def _generate_section_5(self, selections: List) -> str:
        """Generate section 五: 投资者关注.

        Args:
            selections: List of NewsSelection objects

        Returns:
            Formatted section content
        """
        if not selections:
            return "本周暂无投资者动态。"

        content = f"五. 投资者关注\n\n"

        # Sort by starred status and time
        selections_sorted = sorted(
            selections,
            key=lambda s: (not s.starred, s.selected_at or datetime.min),
            reverse=True,
        )

        # Group by investor/institution
        by_investor = {}

        for selection in selections_sorted[:20]:
            article = self.news_repo.get_by_id(selection.news_id)
            if not article:
                continue

            text = article.title + " " + (article.description or "")

            # Find mentioned investor
            investor = None
            for entity in ["PIF", "Mubadala", "ADIA", "ADQ", "QIA", "KIA", "OIA", "2Point0"]:
                if entity.lower() in text.lower():
                    investor = entity
                    break

            if not investor:
                investor = "其他投资机构"

            if investor not in by_investor:
                by_investor[investor] = []

            star = "⭐ " if selection.starred else ""
            by_investor[investor].append({
                "title": article.title,
                "source": article.source,
                "star": star,
            })

        # Build section
        section_num = 1

        for investor, items in list(by_investor.items())[:5]:
            content += f"{section_num}. {investor}\n\n"
            for item in items[:3]:
                content += f"{item['star']}• {item['title']}\n"
                content += f"  来源: {item['source']}\n"
            content += "\n"
            section_num += 1

        return content

    def _generate_section_9(self, selections: List, week_key: str) -> str:
        """Generate section 九: 募资的思考和反思.

        Uses LLM to generate strategic reflection.

        Args:
            selections: List of all NewsSelection objects
            week_key: Week key

        Returns:
            Formatted section content
        """
        content = f"九. 募资的思考和反思\n\n"

        # Use LLM to generate reflection
        reflection = self._generate_reflection_with_llm(selections, week_key)

        if reflection:
            content += reflection
        else:
            content += "本周暂无反思内容。"

        return content

    def _generate_reflection_with_llm(self, selections: List, week_key: str) -> Optional[str]:
        """Generate section 9 using LLM.

        Args:
            selections: List of NewsSelection objects
            week_key: Week key

        Returns:
            Generated reflection text or None
        """
        try:
            import openai

            # Build context from selected articles
            context_items = []
            for selection in selections[:15]:  # Top 15
                article = self.news_repo.get_by_id(selection.news_id)
                if article:
                    context_items.append(f"- {article.title}")

            context = "\n".join(context_items)

            prompt = f"""你是中东募资业务的战略顾问。请根据本周选定的新闻，撰写一份"募资的思考和反思"内部备忘录。

本周周期: {week_key}

选定的新闻摘要:
{context}

请撰写以下内容（中文）:

1. 本周中东资金动态综述
2. 对国内募资工作的启示
3. 下周重点关注方向

要求:
- 语气: 内部战略备忘录
- 视角: 实务导向，链接外部新闻与真实募资执行
- 重点强调: 中东资金对接、国内资源组织、产业主题匹配
- 长度: 500-800字

请直接输出内容，不要添加额外的标题或格式。"""

            response = openai.OpenAI(api_key=self.config.llm.api_key).chat.completions.create(
                model=self.config.llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位经验丰富的中东募资战略顾问，专门为GP/LP提供募资策略建议。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating reflection with LLM: {e}")
            return None
