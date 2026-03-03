#!/usr/bin/env python3
"""
Email client module for sending weekly digest via Resend.

Handles email composition and sending via Resend API.
"""

import logging
import requests
from typing import List, Optional
from datetime import datetime, timezone, timedelta

from .config import get_config
from .topic_cluster import Topic

logger = logging.getLogger(__name__)


# Resend API base URL
RESEND_API_URL = "https://api.resend.com/emails"


class EmailClient:
    """Client for sending emails via Resend API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Resend email client.

        Args:
            api_key: Resend API key (defaults to config).
        """
        config = get_config()
        self.api_key = api_key or config.resend_api_key
        self.from_email = config.email_from
        self.to_emails = config.email_to

        if not self.api_key:
            raise ValueError("RESEND_API_KEY is required for weekly digest")

        if not self.from_email:
            raise ValueError("EMAIL_FROM is required for weekly digest")

        if not self.to_emails:
            raise ValueError("EMAIL_TO is required for weekly digest")

    def send_email(
        self,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email via Resend API.

        Args:
            subject: Email subject.
            html_content: HTML email body.
            text_content: Plain text fallback (optional).

        Returns:
            True if successful.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "from": self.from_email,
            "to": self.to_emails,
            "subject": subject,
            "html": html_content,
        }

        if text_content:
            data["text"] = text_content

        try:
            response = requests.post(RESEND_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Email sent successfully: {result.get('id')}")
            return True

        except requests.RequestException as e:
            logger.error(f"Failed to send email: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False


def format_weekly_digest_html(topics: List[Topic], digest_date: datetime) -> str:
    """Format weekly digest as HTML email.

    Args:
        topics: List of Topic objects (top 10).
        digest_date: Date for the digest.

    Returns:
        HTML email content.
    """
    # Format date in GMT+8
    tz = timezone(timedelta(hours=8))
    date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; }}
        .section {{ background: #f9f9f9; padding: 25px; margin: 20px 0; border-radius: 8px; }}
        .section h2 {{ color: #1e3c72; border-bottom: 3px solid #2a5298; padding-bottom: 10px; margin-top: 0; }}
        .topic {{ background: white; padding: 20px; margin: 15px 0; border-left: 4px solid #2a5298; border-radius: 5px; }}
        .topic h3 {{ color: #2a5298; margin-top: 0; }}
        .topic-meta {{ color: #666; font-size: 14px; margin-bottom: 15px; }}
        .developments {{ margin: 15px 0; }}
        .developments ul {{ margin: 0; padding-left: 20px; }}
        .developments li {{ margin: 8px 0; }}
        .importance {{ background: #e8f4f8; padding: 12px; border-radius: 5px; margin: 15px 0; }}
        .importance strong {{ color: #1e3c72; }}
        .links {{ margin: 15px 0; }}
        .links a {{ color: #2a5298; text-decoration: none; display: block; margin: 5px 0; }}
        .links a:hover {{ text-decoration: underline; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
        .action-list {{ background: #fff8e1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .action-list ol {{ margin: 0; padding-left: 20px; }}
        .action-list li {{ margin: 8px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>本周中东投资/主权基金要闻 Top{len(topics)}</h1>
        <p>{date_str} | 过去7天</p>
    </div>

    <div class="section">
        <h2>一、本周Top10主题</h2>
"""

    for i, topic in enumerate(topics, 1):
        topic_summary = _summarize_topic_for_email(topic)

        html += f"""
        <div class="topic">
            <h3>{i}. {topic.title}</h3>
            <div class="topic-meta">
                📊 相关文章：{topic.article_count}条 |
                🏢 来源数：{topic.source_diversity} |
                ⭐ 主题分数：{topic.topic_score:.1f}
            </div>
            <div class="developments">
                <strong>📌 关键进展：</strong>
                <ul>
"""

        for dev in topic_summary["key_developments"]:
            html += f"                    <li>{dev}</li>\n"

        html += f"""                </ul>
            </div>
            <div class="importance">
                <strong>💡 为什么重要：</strong>
                {topic_summary["why_important"]}
            </div>
            <div class="links">
                <strong>🔗 相关链接：</strong>
"""

        for link in topic_summary["links"]:
            html += f'                <a href="{link["url"]}">{link["title"][:60]}...</a>\n'

        html += """            </div>
        </div>
"""

    html += """    </div>

    <div class="section">
        <h2>二、GCC募资策略与投后赋能服务</h2>

        <h3>🎯 GCC资金方关注要点</h3>
        <ul>
            <li><strong>主权财富基金（SWF）</strong>：治理结构、下行保护、联合投资机会、中国敞口、区域产业战略协同</li>
            <li><strong>养老金/家族办公室</strong>：长期稳定回报、通胀对冲、资产配置多元化、地缘政治风险分散</li>
        </ul>

        <h3>📍 基金定位建议</h3>
        <ul>
            <li>过往业绩 + 专业团队</li>
            <li>项目获取 + 联合投资能力</li>
            <li>本地增值服务能力</li>
            <li>与GCC产业战略的协同</li>
        </ul>

        <h3>🏭 投后赋能服务菜单</h3>

        <h4>医疗健康</h4>
        <ul>
            <li>监管路径指导、准入合规</li>
            <li>分销商/医院集团对接</li>
            <li>医保/支付体系进入策略</li>
            <li>合资结构设计</li>
        </ul>

        <h4>消费</h4>
        <ul>
            <li>渠道进入（沙特/阿联酋）</li>
            <li>电商平台对接</li>
            <li>本地合作伙伴匹配</li>
            <li>清真认证/标签合规</li>
            <li>营销与品牌本地化</li>
        </ul>

        <h4>制造</h4>
        <ul>
            <li>工业区选址与对接</li>
            <li>激励政策协调</li>
            <li>本地化合作伙伴</li>
            <li>采购渠道对接</li>
            <li>EPC承包商链接</li>
        </ul>

        <h4>AI/数据中心/基础设施/科技</h4>
        <ul>
            <li>超大规模云厂商对接</li>
            <li>主权云项目机会</li>
            <li>承购方(offtake)对接</li>
            <li>许可与政府关系协调</li>
            <li>能源合同与绿色电力</li>
        </ul>

        <h3>📋 下周行动清单</h3>
        <div class="action-list">
            <ol>
                <li>联系5家目标LP（主权基金/家族办公室）安排初步会议</li>
                <li>准备2个联合投资方案建议，对接GCC主权基金直投部门</li>
                <li>安排1次被投企业GCC市场路演电话会议</li>
                <li>建立GCC合作伙伴地图（法律/投行/本地服务机构）</li>
            </ol>
        </div>
    </div>

    <div class="footer">
        <p>本邮件由MENA新闻系统自动生成</p>
        <p>主要机构：穆巴达拉(Mubadala)、阿布扎比投资局(ADIA)、ADQ、沙特公共投资基金(PIF)、卡塔尔投资局(QIA)、科威特投资局(KIA)、阿曼投资局(OIA)</p>
    </div>
</body>
</html>
"""

    return html


def _summarize_topic_for_email(topic: Topic) -> dict:
    """Summarize topic for email.

    Args:
        topic: Topic object.

    Returns:
        Dictionary with topic summary.
    """
    # Key developments (top 3 articles)
    key_developments = []
    for article in topic.articles[:3]:
        dev = f"• {article.title[:80]}{'...' if len(article.title) > 80 else ''} ({article.source})"
        key_developments.append(dev)

    # Why important
    if topic.entity:
        why_important = f"该主题涉及{topic.entity}等{('主权基金' if topic.entity else '主要机构')}的重要动向，对区域投资格局有显著影响。"
    else:
        why_important = "该主题反映了当前市场的重要趋势和热点。"

    # Links
    links = []
    for article in topic.articles[:3]:
        if article.url:
            links.append({
                "title": article.title,
                "url": article.url,
            })

    return {
        "key_developments": key_developments,
        "why_important": why_important,
        "links": links,
    }


def format_weekly_digest_text(topics: List[Topic], digest_date: datetime) -> str:
    """Format weekly digest as plain text.

    Args:
        topics: List of Topic objects.
        digest_date: Date for the digest.

    Returns:
        Plain text email content.
    """
    tz = timezone(timedelta(hours=8))
    date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

    lines = [
        f"本周中东投资/主权基金要闻 Top{len(topics)}",
        f"{date_str} | 过去7天",
        "=" * 60,
        "",
        "一、本周Top10主题",
        "",
    ]

    for i, topic in enumerate(topics, 1):
        lines.extend([
            f"{i}. {topic.title}",
            f"   相关文章：{topic.article_count}条 | 来源数：{topic.source_diversity}",
            "",
            "   关键进展：",
        ])

        for article in topic.articles[:3]:
            lines.append(f"   • {article.title[:70]}... ({article.source})")

        lines.extend([
            "",
            f"   为什么重要：{topic.event_type}相关活动对区域投资环境有重要影响。",
            "",
            "   相关链接：",
        ])

        for article in topic.articles[:3]:
            if article.url:
                lines.append(f"   • {article.url}")

        lines.append("")

    lines.extend([
        "=" * 60,
        "",
        "二、GCC募资策略与投后赋能服务",
        "",
        "下周行动：",
        "1. 联系5家目标LP（主权基金/家族办公室）",
        "2. 准备2个联合投资方案建议",
        "3. 安排1次被投企业GCC市场路演",
        "4. 建立GCC合作伙伴地图",
        "",
        "---",
        "本邮件由MENA新闻系统自动生成",
    ])

    return "\n".join(lines)


def send_weekly_digest(topics: List[Topic], digest_date: datetime) -> bool:
    """Send weekly digest email.

    Args:
        topics: List of Topic objects (top 10).
        digest_date: Date for the digest.

    Returns:
        True if successful.
    """
    try:
        client = EmailClient()

        # Format date in GMT+8
        tz = timezone(timedelta(hours=8))
        date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

        subject = f"本周中东投资/主权基金要闻 Top{len(topics)}（{date_str}）"

        html_content = format_weekly_digest_html(topics, digest_date)
        text_content = format_weekly_digest_text(topics, digest_date)

        success = client.send_email(subject, html_content, text_content)

        if success:
            logger.info(f"Weekly digest sent with {len(topics)} topics")

        return success

    except Exception as e:
        logger.error(f"Failed to send weekly digest: {e}")
        return False
