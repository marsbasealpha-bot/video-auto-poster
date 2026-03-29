"""
platforms/tiktok.py - TikTok uploader using tiktok-uploader (Playwright-based).
Session cookies are saved to TIKTOK_SESSION_FILE for reuse.

First-time setup:
  Run: python -c "from tiktok_uploader.auth import AuthBackend; AuthBackend(cookies='tiktok_session.json').authenticate()"
  A browser window will open. Log in manually, then close the browser.
  The session will be saved automatically.
"""
import logging

import config

logger = logging.getLogger(__name__)


def upload(video_path: str, title: str, hashtags: str, description: str):
    """Upload a video to TikTok."""
    try:
        from tiktok_uploader.upload import upload_video
        from tiktok_uploader.auth import AuthBackend
    except ImportError:
        raise ImportError(
            "tiktok-uploader not installed. Run: pip install tiktok-uploader"
        )

    session_file = config.TIKTOK_SESSION_FILE

    caption = f"{title} {hashtags}"[:2200]  # TikTok caption limit

    logger.info(f"Uploading '{title}' to TikTok...")

    auth = AuthBackend(cookies=session_file)
    upload_video(
        video_path,
        description=caption,
        auth=auth,
        headless=True,  # Run browser in background
    )

    logger.info("TikTok upload complete!")
