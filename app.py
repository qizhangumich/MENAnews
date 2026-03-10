#!/usr/bin/env python3
"""
MENA News Intelligence System v2
Main entry point for all jobs and services.

REQUIRES: Python 3.7+
"""
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python app.py <command>")
        print("\nCommands:")
        print("  collect    - Run RSS news collection")
        print("  score      - Run scoring engine on recent articles")
        print("  daily-push - Send daily Telegram push")
        print("  weekly     - Generate and email weekly report")
        print("  bot        - Run Telegram bot (interactive)")
        print("\nExamples:")
        print("  python app.py collect")
        print("  python app.py daily-push")
        return 1

    command = sys.argv[1]

    if command == "collect":
        from jobs.run_collection import main as run_collection
        return run_collection()

    elif command == "score":
        from jobs.run_scoring import main as run_scoring
        return run_scoring()

    elif command == "daily-push":
        from jobs.run_daily_push import main as run_daily_push
        return run_daily_push()

    elif command == "weekly":
        from jobs.run_weekly_report import main as run_weekly_report
        return run_weekly_report()

    elif command == "bot":
        from telegram.bot import run_bot
        run_bot()
        return 0

    else:
        logger.error(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
