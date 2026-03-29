"""
scheduler.py - Human-like delay scheduler.
Adds randomized delays between uploads to avoid spam detection.
"""
import time
import random
import logging

import config

logger = logging.getLogger(__name__)


def human_delay():
    """Wait a random amount of time between POST_DELAY_MIN and POST_DELAY_MAX seconds."""
    delay = random.randint(config.POST_DELAY_MIN, config.POST_DELAY_MAX)
    minutes = delay // 60
    seconds = delay % 60
    logger.info(f"Human delay: waiting {minutes}m {seconds}s before next upload...")
    time.sleep(delay)
