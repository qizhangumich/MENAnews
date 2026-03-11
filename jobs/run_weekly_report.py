#!/usr/bin/env python3
"""
Job: Run weekly report generation and email delivery.
Generates sections 四, 五, 九 and sends via email.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from reports.weekly_generator import WeeklyReportGenerator
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run weekly report job."""
    logger.info("=" * 60)
    logger.info("Starting Weekly Report Job")
    logger.info("=" * 60)

    config = Config()
    generator = WeeklyReportGenerator(config=config)

    report = generator.generate()

    if report:
        logger.info("=" * 60)
        logger.info("Weekly Report Job Complete")
        logger.info(f"Week: {report.week_key}")
        logger.info(f"Sections: 四、五 generated")
        logger.info(f"Email sent to: {', '.join(config.email.email_recipients)}")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("Failed to generate weekly report")
        return 1


if __name__ == "__main__":
    sys.exit(main())
