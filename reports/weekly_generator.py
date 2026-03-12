#!/usr/bin/env python3
"""
Weekly report generator for sections 四, 五, 九.
Generates Chinese reports from top scored articles.
"""
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from storage.selection_repository import get_week_key, NewsSelection
from storage.raw_news_repository import RawNewsRepository
from storage.score_repository import ScoreRepository
from storage.report_repository import WeeklyReport, ReportRepository
from email_sender.sender import EmailSender
from config import Config

logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """Generate weekly reports from top scored articles."""

    def __init__(self, config: Config = None):
        """Initialize generator.

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.news_repo = RawNewsRepository(config=self.config)
        self.score_repo = ScoreRepository(config=self.config)
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

        # Get top scored articles for the week with relevance filter
        min_relevance = self.config.thresholds.weekly_relevance_min
        scores = self.score_repo.get_top_scores(limit=30, week_key=week_key, min_relevance=min_relevance)

        if not scores:
            logger.error(f"No scored articles found for week {week_key} (min_relevance={min_relevance})")
            return None

        # Create selections from top scores
        selections = self._create_selections_from_scores(scores, week_key)
        logger.info(f"Using {len(selections)} top scored articles for weekly report")

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
            email_to=", ".join(self.config.email.email_recipients),
        )

        # Save report
        report_id = self.report_repo.save(report)
        if report_id:
            logger.info(f"Saved report: {report_id}")

        # Send email
        if self.email_sender.send_weekly_report(report):
            self.report_repo.mark_email_sent(week_key, ", ".join(self.config.email.email_recipients))
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

            # Get Chinese translation and analysis
            translated = self._translate_and_analyze_article(article, focus="募资")

            star = "⭐ " if selection.starred else ""
            item = f"{star}• {translated['content']}\n"

            text = (article.title + " " + (article.description or "")).lower()

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

            # Get Chinese translation and analysis
            translated = self._translate_and_analyze_article(article, focus="投资")

            star = "⭐ " if selection.starred else ""
            by_investor[investor].append({
                "content": translated['content'],
                "star": star,
            })

        # Build section
        section_num = 1

        for investor, items in list(by_investor.items())[:5]:
            content += f"{section_num}. {investor}\n\n"
            for item in items[:3]:
                content += f"{item['star']}• {item['content']}\n"
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

    def _translate_and_analyze_article(self, article, focus: str = "募资") -> dict:
        """Translate article to Chinese and generate impact analysis.

        Args:
            article: RawNews object
            focus: Focus area ("募资" or "投资")

        Returns:
            Dictionary with translated title and analysis
        """
        try:
            import openai

            title = article.title or "无标题"
            description = article.snippet_text or article.description or ""

            prompt = f"""请将以下新闻翻译成详细的中文摘要（200-300字），包括标题和分析。

新闻标题: {title}
新闻内容: {description[:1000]}

请按以下格式输出（JSON格式）:
{{
    "content": "完整的中文摘要（200-300字），包含：1）新闻要点（公司、金额、交易类型等）；2）对中东经济和募资市场的影响分析"
}}

要求:
- 总长度必须达到200-300字
- 第一部分：详细翻译新闻关键信息（公司名称、交易金额、交易类型、市场背景等）
- 第二部分：分析此新闻对中东主权财富基金、募资市场的具体影响（LP配置变化、投资机会、市场趋势等）
- 内容要丰富具体，不要笼统概括
- 直接输出JSON，不要有其他内容

示例格式:
"黑石集团与EQT计划以334亿美元收购全球电力公司AES，这是今年以来最大的基础设施收购案之一，显示出全球顶级资本正在加速布局能源转型基础设施。此交易反映出基础设施与能源转型已成为全球资本重要配置领域，中东LP可重点关注相关 mega-fund 的配置机会，同时ESG 基础设施投资正成为新的投资主题。"
"""

            response = openai.OpenAI(api_key=self.config.llm.api_key).chat.completions.create(
                model=self.config.llm.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的中东经济和募资市场分析师，擅长将英文新闻翻译成详细的中文并分析其对中东募资的影响。"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=600,
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            import json
            try:
                result = json.loads(result_text)
                return {
                    "content": result.get("content", f"{title}\n\n相关市场动态")
                }
            except json.JSONDecodeError:
                # Fallback: return original title and simple analysis
                return {
                    "content": f"{title}\n\n相关市场动态"
                }

        except Exception as e:
            logger.error(f"Error translating article: {e}")
            return {
                "content": article.title or "无标题"
            }

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

    def _create_selections_from_scores(self, scores: List, week_key: str) -> List:
        """Create selection objects from score objects.

        Args:
            scores: List of NewsScore objects
            week_key: Week key

        Returns:
            List of NewsSelection objects
        """
        selections = []
        for score in scores:
            # Use section_suggested from scoring engine, or assign based on content
            if score.section_suggested and len(score.section_suggested) > 0:
                sections = score.section_suggested
            else:
                # Fallback: determine from article content
                article = self.news_repo.get_by_id(score.news_id)
                if article:
                    text = (article.title + " " + (article.description or "")).lower()
                    # Check for section 5 keywords (SWF/investor focus)
                    if any(kw in text for kw in ["pif", "mubadala", "adia", "qia", "kia", "adq", "oia", "sovereign wealth"]):
                        sections = ["5"]
                    else:
                        # Default to section 4 (market dynamics)
                        sections = ["4"]
                else:
                    sections = ["4"]

            selection = NewsSelection(
                news_id=score.news_id,
                week_key=week_key,
                selected_sections=sections,
                starred=False,
                selected_at=datetime.now(timezone.utc),
            )
            selections.append(selection)

        return selections
