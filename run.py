#!/usr/bin/env python3
"""
MENA News Collector - Runner

Entry point that runs the scheduler.
Executed by OpenClaw via Telegram.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scheduler import main


if __name__ == "__main__":
    main()
