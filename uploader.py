"""
uploader.py - Upload orchestrator.
Calls each enabled platform uploader with human-like delays in between.
"""
import os
import re
import logging
import config
from scheduler import human_delay

logger = logging.getLogger(__name__)


def _parse_metadata(filename: str):
    """
    Extract title, hashtags, and description from a video filename.
    Example: 'My Cool Video #fyp #viral.mp4' -> ('My Cool Video', '#fyp #viral', '')
    """
    stem = os.path.splitext(os.path.basename(filename))[0]  # strip extension
    # Find all hashtags
    tags = re.findall(r'#\w+', stem)
    hashtags = " ".join(tags) if tags else config.DEFAULT_HASHTAGS
    # Title is everything before the first hashtag
    title = re.split(r'\s*#', stem)[0].strip()
    if not title:
        title = config.DEFAULT_TITLE
    return title, hashtags, config.DEFAULT_DESCRIPTION

class Uploader:
    def __init__(self):
        # Platform modules are imported lazily to avoid circular dependencies
        self.platforms = []
        self._initialize_platforms()

    def _initialize_platforms(self):
        if config.ENABLE_YOUTUBE:
            from platforms.youtube import upload as yt_upload
            self.platforms.append(("YouTube Shorts", yt_upload))
        if config.ENABLE_TIKTOK:
            from platforms.tiktok import upload as tt_upload
            self.platforms.append(("TikTok", tt_upload))
        if config.ENABLE_INSTAGRAM:
            from platforms.instagram import upload as ig_upload
            self.platforms.append(("Instagram Reels", ig_upload))
        if config.ENABLE_X:
            from platforms.x import upload as x_upload
            self.platforms.append(("X (Twitter)", x_upload))
        if config.ENABLE_RUMBLE:
            from platforms.rumble import upload as rb_upload
            self.platforms.append(("Rumble", rb_upload))
        if config.ENABLE_TRUTHSOCIAL:
            from platforms.truthsocial import upload as ts_upload
            self.platforms.append(("Truth Social", ts_upload))

    def _check_credentials(self, name):
        """Check if required credentials exist for a platform. Returns error message or None."""
        if name == "YouTube Shorts":
            secret = config.YOUTUBE_CLIENT_SECRET
            if not secret or not os.path.exists(secret):
                return "client_secret.json not found. Set it in Setup Wizard > YouTube tab."
        elif name == "TikTok":
            session = config.TIKTOK_SESSION_FILE
            if not session or not os.path.exists(session):
                return f"Cookies file not found: {session or '(not set)'}. Export cookies via Setup Wizard > TikTok tab."
        elif name == "Instagram Reels":
            if not config.INSTAGRAM_USERNAME or config.INSTAGRAM_USERNAME == "your_username":
                return "Username not configured. Set it in Setup Wizard > Instagram tab."
            if not config.INSTAGRAM_PASSWORD:
                return "Password not configured. Set it in Setup Wizard > Instagram tab."
        elif name == "X (Twitter)":
            session = config.X_SESSION_FILE
            if not session or not os.path.exists(session):
                return f"Session file not found: {session or '(not set)'}. Use Setup Wizard > X tab > Login Helper."
        elif name == "Rumble":
            if not config.RUMBLE_USERNAME:
                return "Username not configured. Set it in Setup Wizard > Rumble tab."
            if not config.RUMBLE_PASSWORD:
                return "Password not configured. Set it in Setup Wizard > Rumble tab."
        elif name == "Truth Social":
            if not config.TRUTHSOCIAL_USERNAME:
                return "Username not configured. Set it in Setup Wizard > Truth Social tab."
            if not config.TRUTHSOCIAL_PASSWORD:
                return "Password not configured. Set it in Setup Wizard > Truth Social tab."
        return None

    def upload_all(self, video_path: str, title: str, hashtags: str, description: str = ""):
        """
        Upload a video to all enabled platforms.
        """
        if not self.platforms:
            logger.warning("No platforms enabled. Skipping upload.")
            return

        for i, (name, upload_fn) in enumerate(self.platforms):
            # Pre-check credentials before attempting upload
            cred_error = self._check_credentials(name)
            if cred_error:
                logger.warning(f"[{name}] Skipped — {cred_error}")
                continue

            try:
                logger.info(f"Uploading to {name}...")
                upload_fn(
                    video_path=video_path,
                    title=title,
                    hashtags=hashtags,
                    description=description,
                )
                logger.info(f"Successfully uploaded to {name}.")
            except Exception as e:
                logger.error(f"Failed to upload to {name}: {e}", exc_info=True)

            # Human delay between platforms (but not after the last one)
            if i < len(self.platforms) - 1:
                human_delay()
