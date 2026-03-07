#!/usr/bin/env python3
"""
Email client module for sending weekly digest via SMTP.

Handles email composition and sending via SMTP (supports 163.com, Gmail, etc.).
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import socket

from .config import get_config
from .summarizer import ArticleSummary

logger = logging.getLogger(__name__)


class EmailClient:
    """Client for sending emails via SMTP."""

    def __init__(self, smtp_config: Optional[dict] = None):
        """Initialize SMTP email client.

        Args:
            smtp_config: SMTP configuration dict (defaults to environment variables).
        """
        config = get_config()

        # Get SMTP config from parameter or environment
        if smtp_config:
            self.smtp_host = smtp_config.get("SMTP_HOST")
            self.smtp_port = int(smtp_config.get("SMTP_PORT", 465))
            self.smtp_user = smtp_config.get("SMTP_USER")
            self.smtp_password = smtp_config.get("SMTP_PASSWORD")
            self.smtp_use_ssl = smtp_config.get("SMTP_USE_SSL", "1") == "1"
            self.smtp_use_tls = smtp_config.get("SMTP_USE_TLS", "0") == "1"
            self.from_email = smtp_config.get("SMTP_USER")  # Use SMTP username as from
            self.to_emails = smtp_config.get("EMAIL_RECIPIENTS", "").split(",")
        else:
            # Try environment variables
            self.smtp_host = os.getenv("SMTP_HOST")
            self.smtp_port = int(os.getenv("SMTP_PORT", 465))
            self.smtp_user = os.getenv("SMTP_USER")
            self.smtp_password = os.getenv("SMTP_PASSWORD")
            self.smtp_use_ssl = os.getenv("SMTP_USE_SSL", "1") == "1"
            self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "0") == "1"
            self.from_email = os.getenv("SMTP_USER", os.getenv("EMAIL_FROM"))
            self.to_emails = [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()]

        # Validate required fields
        if not self.smtp_host:
            raise ValueError("SMTP_HOST is required for weekly digest")

        if not self.smtp_user:
            raise ValueError("SMTP_USER is required for weekly digest")

        if not self.smtp_password:
            raise ValueError("SMTP_PASSWORD is required for weekly digest")

        if not self.to_emails:
            raise ValueError("EMAIL_RECIPIENTS is required for weekly digest")

    def send_email(
        self,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email via SMTP.

        Args:
            subject: Email subject.
            html_content: HTML email body.
            text_content: Plain text fallback (optional).

        Returns:
            True if successful.
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)

            # Add plain text version
            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))

            # Add HTML version
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # Connect to SMTP server
            if self.smtp_use_ssl:
                # SSL connection (port 465 typically)
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                # TLS connection (port 587 or 25 typically)
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                if self.smtp_use_tls:
                    server.starttls()

            # Login
            server.login(self.smtp_user, self.smtp_password)

            # Send email
            server.sendmail(self.from_email, self.to_emails, msg.as_string())

            # Quit
            server.quit()

            logger.info(f"Email sent successfully to {len(self.to_emails)} recipients")
            return True

        except socket.gaierror as e:
            logger.error(f"SMTP connection error (DNS/Network): {e}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}")
            logger.error("Check your SMTP username and password")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


import os


def format_weekly_digest_html(summaries: List[ArticleSummary], digest_date: datetime) -> str:
    """Format weekly digest as HTML email with 60 bilingual articles.

    Args:
        summaries: List of ArticleSummary objects (top 60).
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
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .header h1 {{ margin: 0; font-size: 26px; }}
        .header p {{ margin: 10px 0 0; opacity: 0.9; font-size: 16px; }}
        .content {{ background: white; padding: 30px; border-radius: 0 0 10px 10px; }}
        .article {{ padding: 20px; margin-bottom: 20px; border-left: 4px solid #2a5298; background: #f9f9f9; border-radius: 5px; }}
        .article h4 {{ color: #1e3c72; margin-top: 0; margin-bottom: 10px; font-size: 18px; }}
        .subtitle {{ color: #666; font-style: italic; margin-bottom: 15px; font-size: 15px; }}
        .summary-cn {{ color: #333; margin-bottom: 10px; line-height: 1.5; }}
        .summary-en {{ color: #555; font-size: 14px; line-height: 1.5; }}
        .meta {{ background: #e8f4f8; padding: 10px; border-radius: 4px; font-size: 13px; color: #666; }}
        .meta a {{ color: #2a5298; text-decoration: none; font-weight: 500; }}
        .meta a:hover {{ text-decoration: underline; }}
        .footer {{ text-align: center; padding: 20px; color: #888; font-size: 13px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>本周中东投资要闻 Top{len(summaries)} (Bilingual)</h1>
        <p>📅 {date_str} | 过去7天 | Past 7 Days</p>
    </div>

    <div class="content">
"""

    for summary in summaries:
        html += summary.to_html(summaries.index(summary) + 1)

    html += """    </div>

    <div class="footer">
        <p>本邮件由MENA新闻系统自动生成 | This email was automatically generated by MENA News System</p>
        <p>主要关注：主权基金(SWF)、并购(M&A)、IPO、私募股权(PE)、风险投资(VC)</p>
        <p>Key Focus: Sovereign Wealth Funds, M&A, IPO, Private Equity, Venture Capital</p>
    </div>
</body>
</html>
"""

    return html


def format_weekly_digest_text(summaries: List[ArticleSummary], digest_date: datetime) -> str:
    """Format weekly digest as plain text.

    Args:
        summaries: List of ArticleSummary objects.
        digest_date: Date for the digest.

    Returns:
        Plain text email content.
    """
    tz = timezone(timedelta(hours=8))
    date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

    lines = [
        f"本周中东投资要闻 Top{len(summaries)} (Bilingual Weekly Digest)",
        f"📅 {date_str} | 过去7天 | Past 7 Days",
        "=" * 70,
        "",
    ]

    for summary in summaries:
        lines.extend([
            f"{summaries.index(summary) + 1}. {summary.title_cn}",
            f"   {summary.title_en}",
            "",
            f"   中文摘要 | Chinese Summary:",
            f"   {summary.summary_cn}",
            "",
            f"   English Summary:",
            f"   {summary.summary_en}",
            "",
            f"   标签 | Tags: {summary.tags}",
            "",
            "-" * 50,
            "",
        ])

    lines.extend([
        "=" * 70,
        "",
        "本邮件由MENA新闻系统自动生成",
        "主要关注：主权基金(SWF)、并购(M&A)、IPO、私募股权(PE)、风险投资(VC)",
        "",
        "---",
    ])

    return "\n".join(lines)


def send_weekly_digest(summaries: List[ArticleSummary], digest_date: datetime) -> bool:
    """Send weekly digest email.

    Args:
        summaries: List of ArticleSummary objects (top 60).
        digest_date: Date for the digest.

    Returns:
        True if successful.
    """
    try:
        client = EmailClient()

        # Format date in GMT+8
        tz = timezone(timedelta(hours=8))
        date_str = digest_date.astimezone(tz).strftime("%Y-%m-%d")

        subject = f"本周中东投资要闻 Top{len(summaries)}（{date_str}）Bilingual"

        html_content = format_weekly_digest_html(summaries, digest_date)
        text_content = format_weekly_digest_text(summaries, digest_date)

        success = client.send_email(subject, html_content, text_content)

        if success:
            logger.info(f"Weekly digest sent with {len(summaries)} articles")

        return success

    except Exception as e:
        logger.error(f"Failed to send weekly digest: {e}")
        return False
