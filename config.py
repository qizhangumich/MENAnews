#!/usr/bin/env python3
"""
Central configuration for MENA News Intelligence System.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"


def load_env():
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)


load_env()


@dataclass
class ScoreWeights:
    """Scoring weights that can be adjusted."""
    relevance_weight: float = 0.65
    importance_weight: float = 0.35
    selection_score_default: int = 0
    selection_score_selected: int = 100


@dataclass
class Thresholds:
    """Score thresholds for filtering."""
    daily_push_threshold: float = 0.0  # Lowered from 25.0 to get more articles initially
    relevance_min: float = 10.0
    importance_min: float = 15.0


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    daily_push_limit: int = 20


@dataclass
class FirestoreConfig:
    """Firestore configuration."""
    project_id: str = field(default_factory=lambda: os.getenv("FIREBASE_PROJECT_ID", "menanews-4a30c"))
    credentials_path: str = field(default_factory=lambda: os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))


@dataclass
class EmailConfig:
    """Email configuration."""
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "smtp.163.com"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "465")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    # Support multiple recipients (comma-separated)
    email_recipients: list = field(default_factory=lambda: (
        [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()]
        or [os.getenv("EMAIL_TO", "zhangqi@cpe-fund.com")]
    ))


@dataclass
class LLMConfig:
    """LLM configuration for weekly report generation."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = "gpt-4o-mini"


@dataclass
class Config:
    """Main configuration class."""
    score_weights: ScoreWeights = field(default_factory=ScoreWeights)
    thresholds: Thresholds = field(default_factory=Thresholds)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    firestore: FirestoreConfig = field(default_factory=FirestoreConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Collection names
    collection_feed_sources: str = "feed_sources"
    collection_news_raw: str = "news_raw"
    collection_news_scores: str = "news_scores"
    collection_news_selection: str = "news_selection"
    collection_telegram_push_log: str = "telegram_push_log"
    collection_weekly_reports: str = "weekly_reports"
    collection_system_config: str = "system_config"


# Global config instance
config = Config()
