#!/usr/bin/env python3
"""
Main entry point for MENA News Ranking Service.

CLI interface for running daily and weekly digests.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('ranking_service.log')
    ]
)

logger = logging.getLogger(__name__)


def run_daily() -> int:
    """Run daily digest pipeline.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from .daily_digest import run_daily_digest

    logger.info("=" * 60)
    logger.info("Running Daily Digest Pipeline")
    logger.info("=" * 60)

    try:
        result = run_daily_digest()

        # Print summary
        print("\n" + "=" * 60)
        print("DAILY DIGEST SUMMARY")
        print("=" * 60)
        print(f"Articles processed: {result.get('articles_processed', 0)}")
        print(f"Articles sent: {result.get('articles_sent', 0)}")
        print(f"Telegram status: {result.get('telegram_status', 'unknown')}")

        if result.get('top_titles'):
            print("\nTop articles:")
            for i, title in enumerate(result.get('top_titles', []), 1):
                print(f"  {i}. {title[:80]}{'...' if len(title) > 80 else ''}")

        print("=" * 60)

        if result.get('success'):
            print("SUCCESS: Daily digest completed successfully")
            return 0
        else:
            error = result.get('error', 'Unknown error')
            print(f"ERROR: {error}")
            return 1

    except Exception as e:
        logger.error(f"Daily digest failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


def run_weekly() -> int:
    """Run weekly digest pipeline.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from .weekly_digest import run_weekly_digest

    logger.info("=" * 60)
    logger.info("Running Weekly Digest Pipeline")
    logger.info("=" * 60)

    try:
        result = run_weekly_digest()

        # Print summary
        print("\n" + "=" * 60)
        print("WEEKLY DIGEST SUMMARY")
        print("=" * 60)
        print(f"Articles processed: {result.get('articles_processed', 0)}")
        print(f"Relevant articles: {result.get('relevant_articles', 0)}")
        print(f"Topics found: {result.get('topics_found', 0)}")
        print(f"Topics sent: {result.get('topics_sent', 0)}")
        print(f"Email status: {result.get('email_status', 'unknown')}")

        if result.get('top_topics'):
            print("\nTop topics:")
            for i, topic in enumerate(result.get('top_topics', []), 1):
                print(f"  {i}. [{topic['score']:.1f}] {topic['title'][:60]}... ({topic['articles']} articles)")

        print("=" * 60)

        if result.get('success'):
            print("SUCCESS: Weekly digest completed successfully")
            return 0
        else:
            error = result.get('error', 'Unknown error')
            print(f"ERROR: {error}")
            return 1

    except Exception as e:
        logger.error(f"Weekly digest failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1


def run_test() -> int:
    """Run test mode to verify configuration.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from .config import get_config
    from .firestore_client import FirestoreClient

    try:
        config = get_config()
        config.validate()

        print("Configuration OK")
        print(f"Firebase project: {config.firebase_project_id}")
        print(f"Firestore collection: {config.firestore_collection}")
        print(f"Telegram configured: {bool(config.telegram_bot_token)}")
        print(f"Email configured: {bool(config.resend_api_key)}")
        print(f"OpenAI available: {config.has_openai()}")

        # Test Firestore connection
        print("\nTesting Firestore connection...")
        db = FirestoreClient()
        db.connect()

        # Test query
        articles = db.query_daily_articles(hours_back=24, limit=5)
        print(f"Successfully queried {len(articles)} recent articles")

        if articles:
            print("\nRecent articles:")
            for i, article in enumerate(articles[:3], 1):
                print(f"  {i}. {article.title[:60]}...")

        print("\nAll tests passed!")
        return 0

    except Exception as e:
        print(f"\nERROR: {e}")
        return 1


def main() -> int:
    """Main entry point.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        description="MENA News Ranking Service - Daily Telegram and Weekly Email Digests"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Daily digest command
    daily_parser = subparsers.add_parser("daily", help="Run daily Telegram digest")

    # Weekly digest command
    weekly_parser = subparsers.add_parser("weekly", help="Run weekly email digest")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test configuration and connection")

    # Parse args
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run command
    if args.command == "daily":
        return run_daily()
    elif args.command == "weekly":
        return run_weekly()
    elif args.command == "test":
        return run_test()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
