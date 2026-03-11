#!/usr/bin/env python3
"""
Email sender for weekly reports.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timezone

from storage.report_repository import WeeklyReport
from config import Config

logger = logging.getLogger(__name__)


class EmailSender:
    """Send emails via SMTP."""

    def __init__(self, config: Config = None):
        """Initialize email sender.

        Args:
            config: Configuration object
        """
        self.config = config or Config()

    def send_weekly_report(self, report: WeeklyReport) -> bool:
        """Send weekly report via email.

        Args:
            report: WeeklyReport object

        Returns:
            True if successful
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"MENA Weekly Fundraising Report | {report.week_key}"
            msg["From"] = formataddr(("MENA News System", self.config.email.smtp_user))
            msg["To"] = ", ".join(self.config.email.email_recipients)

            # Create plain text content
            text_content = self._format_text_report(report)

            # Create HTML content
            html_content = self._format_html_report(report)

            # Attach both versions
            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")

            msg.attach(part1)
            msg.attach(part2)

            # Send via SMTP
            return self._send_smtp(msg, self.config.email.email_recipients)

        except Exception as e:
            logger.error(f"Error sending weekly report email: {e}")
            return False

    def _send_smtp(self, msg, to_addrs: list) -> bool:
        """Send message via SMTP.

        Args:
            msg: Email message
            to_addrs: List of recipient addresses

        Returns:
            True if successful
        """
        try:
            if self.config.email.smtp_port == 465:
                # SSL
                server = smtplib.SMTP_SSL(
                    self.config.email.smtp_host,
                    self.config.email.smtp_port,
                    timeout=30,
                )
            else:
                # TLS
                server = smtplib.SMTP(
                    self.config.email.smtp_host,
                    self.config.email.smtp_port,
                    timeout=30,
                )
                server.starttls()

            server.login(self.config.email.smtp_user, self.config.email.smtp_password)
            server.send_message(msg, to_addrs=to_addrs)
            server.quit()

            logger.info(f"Email sent successfully to {', '.join(to_addrs)}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    def _format_text_report(self, report: WeeklyReport) -> str:
        """Format report as plain text.

        Args:
            report: WeeklyReport object

        Returns:
            Plain text report
        """
        return f"""MENA Weekly Fundraising Report | {report.week_key}
Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

------------------------------------------------------------

{report.section_4}

------------------------------------------------------------

{report.section_5}

------------------------------------------------------------

{report.section_9}

------------------------------------------------------------

End of Report
"""

    def _format_html_report(self, report: WeeklyReport) -> str:
        """Format report as HTML.

        Args:
            report: WeeklyReport object

        Returns:
            HTML report
        """
        # Convert plain text sections to HTML paragraphs
        def text_to_html(text):
            paragraphs = text.split("\n\n")
            html = ""
            for para in paragraphs:
                para = para.replace("\n", "<br>")
                html += f"<p>{para}</p>"
            return html

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Arial', 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .meta {{ color: #7f8c8d; font-size: 14px; }}
        .section {{ margin: 20px 0; }}
        hr {{ border: none; border-top: 1px solid #ecf0f1; margin: 30px 0; }}
    </style>
</head>
<body>
    <h1>MENA Weekly Fundraising Report | {report.week_key}</h1>
    <div class="meta">Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</div>

    <hr>

    <div class="section">
        {text_to_html(report.section_4)}
    </div>

    <hr>

    <div class="section">
        {text_to_html(report.section_5)}
    </div>

    <hr>

    <div class="section">
        {text_to_html(report.section_9)}
    </div>

    <hr>

    <div class="meta">End of Report</div>
</body>
</html>
"""
