#!/usr/bin/env python3
"""
Configuration module for MENA News Ranking Service.

Handles environment variables and application settings.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Config:
    """Application configuration."""

    # Firestore
    firebase_project_id: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID", "menanews-4a30c"))
    firestore_collection: str = field(default_factory=lambda: os.getenv("FIRESTORE_COLLECTION", "news"))
    google_credentials_path: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))

    # Telegram
    telegram_bot_token: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN"))
    telegram_chat_id: Optional[str] = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID"))

    # Email (SMTP - 163.com, Gmail, etc.)
    smtp_host: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "465")))
    smtp_user: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USER"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    smtp_use_ssl: bool = field(default_factory=lambda: os.getenv("SMTP_USE_SSL", "1") == "1")
    smtp_use_tls: bool = field(default_factory=lambda: os.getenv("SMTP_USE_TLS", "0") == "1")
    email_recipients: List[str] = field(default_factory=lambda: (
        [email.strip() for email in os.getenv("EMAIL_RECIPIENTS", "").split(",") if email.strip()]
        if os.getenv("EMAIL_RECIPIENTS") else []
    ))

    # Email (Resend - optional alternative)
    resend_api_key: Optional[str] = field(default_factory=lambda: os.getenv("RESEND_API_KEY"))
    email_from: Optional[str] = field(default_factory=lambda: os.getenv("EMAIL_FROM"))
    email_to: List[str] = field(default_factory=lambda: (
        [email.strip() for email in os.getenv("EMAIL_TO", "").split(",") if email.strip()]
        if os.getenv("EMAIL_TO") else []
    ))

    # OpenAI (optional)
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

    # Timezone
    digest_timezone: str = field(default_factory=lambda: os.getenv("DIGEST_TIMEZONE", "Asia/Shanghai"))

    # Scoring thresholds
    daily_relevance_threshold: int = 25
    daily_top_n: int = 10
    weekly_top_topics: int = 10

    # Query limits
    daily_max_docs: int = 500
    weekly_max_docs: int = 2000

    # Daily digest time (GMT+8)
    daily_digest_hour: int = 8
    daily_digest_minute: int = 30

    # Weekly digest time (GMT+8)
    weekly_digest_day: int = 4  # Friday (0=Monday, 6=Sunday)
    weekly_digest_hour: int = 8
    weekly_digest_minute: int = 30

    def validate(self) -> None:
        """Validate required configuration."""
        errors = []

        if not self.google_credentials_path and not os.path.exists("firebase_service_account.json"):
            # Check if credentials file exists in default location
            if not os.path.exists(os.path.expanduser("~/.config/firebase_service_account.json")):
                errors.append("Firebase credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or place firebase_service_account.json in project root.")

        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required for daily digest.")

        if not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID is required for daily digest.")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    def validate_email(self) -> None:
        """Validate email configuration for weekly digest."""
        errors = []

        # Check for SMTP configuration (preferred)
        if self.smtp_host and self.smtp_user and self.smtp_password:
            # SMTP is configured
            if not self.email_recipients:
                errors.append("EMAIL_RECIPIENTS is required for weekly email digest.")
            return

        # Fallback to Resend API
        if not self.resend_api_key:
            errors.append("Either SMTP configuration (SMTP_HOST, SMTP_USER, SMTP_PASSWORD) or RESEND_API_KEY is required for weekly email digest.")

        if not self.email_from:
            errors.append("EMAIL_FROM is required for weekly email digest (when using Resend).")

        if not self.email_to:
            errors.append("EMAIL_TO is required for weekly email digest (when using Resend).")

        if errors:
            raise ValueError("Email configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    def has_openai(self) -> bool:
        """Check if OpenAI API key is available."""
        return bool(self.openai_api_key)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global config instance (singleton)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment variables."""
    global _config
    _config = Config()
    return _config
