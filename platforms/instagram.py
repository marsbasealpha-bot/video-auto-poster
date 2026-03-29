"""
platforms/instagram.py - Instagram Reels uploader using instagrapi.
Session is saved to INSTAGRAM_SESSION_FILE for reuse.

On first run, it will log in with username/password and save the session.
If a challenge (SMS/Email verification) is triggered, the script will prompt
you to enter the code in the terminal.
"""
import os
import logging

import config

logger = logging.getLogger(__name__)


def _get_client():
    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired, ChallengeRequired
    except ImportError:
        raise ImportError(
            "instagrapi not installed. Run: pip install instagrapi"
        )

    cl = Client()
    session_file = config.INSTAGRAM_SESSION_FILE

    if os.path.exists(session_file):
        logger.info(f"Loading Instagram session from {session_file}...")
        try:
            cl.load_settings(session_file)
            cl.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
            cl.get_timeline_feed()  # Test if session is valid
            logger.info("Instagram session restored successfully.")
            return cl
        except (LoginRequired, Exception) as e:
            logger.warning(f"Saved session invalid ({e}), re-logging in...")

    # Fresh login
    logger.info(f"Logging in to Instagram as @{config.INSTAGRAM_USERNAME}...")
    username = config.INSTAGRAM_USERNAME
    password = config.INSTAGRAM_PASSWORD

    if not username or not password:
        raise ValueError(
            "Instagram credentials not set. "
            "Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in your .env file."
        )

    try:
        cl.login(username, password)
    except Exception as e:
        # Handle challenges (e.g., 2FA, suspicious login)
        if "challenge" in str(e).lower():
            logger.warning("Instagram challenge detected. Attempting challenge resolution...")
            # instagrapi handles TOTP / SMS in some cases automatically
            raise
        raise

    cl.dump_settings(session_file)
    logger.info(f"Instagram session saved to {session_file}.")
    return cl


def upload(video_path: str, title: str, hashtags: str, description: str):
    """Upload a video as an Instagram Reel."""
    cl = _get_client()

    caption = f"{title}\n\n{description}\n\n{hashtags}".strip()

    logger.info(f"Uploading '{title}' to Instagram Reels...")
    media = cl.clip_upload(
        path=video_path,
        caption=caption,
    )

    logger.info(f"Instagram Reel uploaded! Media PK: {media.pk}")
    logger.info(f"URL: https://www.instagram.com/reel/{media.code}/")
