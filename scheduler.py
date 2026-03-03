#!/usr/bin/env python3
"""
Scheduler for Sovereign News Collector

Runs the news collector on a scheduled interval (default: every 1 hour).
Can be run as a long-running process or used as a reference for cron setup.
"""

import logging
import signal
import sys
import time
from datetime import datetime

import schedule

from collector import NewsCollector, logger
from firebase_config import initialize_firestore


# Scheduled interval in minutes (default: 60 minutes = 1 hour)
SCHEDULE_INTERVAL_MINUTES = 60


class Scheduler:
    """Scheduler for running news collector periodically."""

    def __init__(self, interval_minutes: int = SCHEDULE_INTERVAL_MINUTES):
        """
        Initialize the scheduler.

        Args:
            interval_minutes: Interval between collection runs in minutes
        """
        self.interval_minutes = interval_minutes
        self.running = False
        self.db = None

    def _run_collection(self):
        """Execute a single collection run."""
        logger.info("=" * 50)
        logger.info(f"Starting scheduled collection run at {datetime.now()}")
        logger.info("=" * 50)

        try:
            # Re-initialize database connection for each run
            self.db = initialize_firestore()
            collector = NewsCollector(self.db)
            collector.collect()

        except Exception as e:
            logger.error(f"Collection run failed: {e}", exc_info=True)

        logger.info(f"Collection run completed at {datetime.now()}")

    def start(self):
        """Start the scheduled execution."""
        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Schedule the job
        schedule.every(self.interval_minutes).minutes.do(self._run_collection)

        logger.info("=" * 50)
        logger.info("News Collector Scheduler Started")
        logger.info(f"Interval: Every {self.interval_minutes} minutes")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 50)

        # Run immediately on start
        self._run_collection()

        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds
            except KeyboardInterrupt:
                self.stop()
                break

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def stop(self):
        """Stop the scheduled execution."""
        self.running = False
        logger.info("Scheduler stopped")


def main():
    """Main entry point for the scheduler."""
    try:
        scheduler = Scheduler(interval_minutes=SCHEDULE_INTERVAL_MINUTES)
        scheduler.start()
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
