"""
main.py - Entry point for the Video Auto-Poster background service.
Run this script to start monitoring the Uploads folder and processing new videos.
"""
import logging
import sys

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("video_auto_poster.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def _check_credentials():
    """Check for placeholder/missing credentials and offer to run setup wizard."""
    import config
    issues = []
    if config.ENABLE_YOUTUBE and (not config.YOUTUBE_CLIENT_SECRET or not os.path.exists(config.YOUTUBE_CLIENT_SECRET)):
        issues.append("YouTube: client_secret.json not found")
    if config.ENABLE_TIKTOK and (not config.TIKTOK_SESSION_FILE or not os.path.exists(config.TIKTOK_SESSION_FILE)):
        issues.append("TikTok: session/cookies file not found")
    if config.ENABLE_INSTAGRAM and (not config.INSTAGRAM_USERNAME or config.INSTAGRAM_USERNAME == "your_username"):
        issues.append("Instagram: username not configured")
    if config.ENABLE_X and (not config.X_SESSION_FILE or not os.path.exists(config.X_SESSION_FILE)):
        issues.append("X (Twitter): session file not found")
    if not config.GEMINI_API_KEY:
        issues.append("Gemini AI: API key not set (mock titles will be used)")

    if issues:
        logger.warning("─── Missing Credentials ───")
        for issue in issues:
            logger.warning(f"  ⚠  {issue}")
        logger.warning("Run 'python setup_wizard.py' to configure.")

        # Try to show a popup if possible
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            msg = "The following credentials are missing:\n\n"
            msg += "\n".join(f"• {i}" for i in issues)
            msg += "\n\nWould you like to open the Setup Wizard?"
            if messagebox.askyesno("Setup Required", msg):
                root.destroy()
                import subprocess
                subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), "setup_wizard.py")])
                logger.info("Setup wizard launched. Restart main.py after saving.")
                sys.exit(0)
            root.destroy()
        except Exception:
            pass  # No display / tkinter not available — continue anyway


def main():
    logger.info("=" * 60)
    logger.info("  Video Auto-Poster - Starting Up")
    logger.info("=" * 60)

    import config

    logger.info(f"Watch folder : {config.WATCH_FOLDER}")
    logger.info(f"YouTube      : {'ON' if config.ENABLE_YOUTUBE else 'OFF'}")
    logger.info(f"TikTok       : {'ON' if config.ENABLE_TIKTOK else 'OFF'}")
    logger.info(f"Instagram    : {'ON' if config.ENABLE_INSTAGRAM else 'OFF'}")
    logger.info(
        f"Post delay   : {config.POST_DELAY_MIN // 60}-{config.POST_DELAY_MAX // 60} min"
    )
    logger.info("-" * 60)
    logger.info("Drop a video into the watch folder to trigger an upload.")
    logger.info("Name your video like: 'My Title #tag1 #tag2.mp4' to set metadata.")
    logger.info("Press Ctrl+C to stop.")
    logger.info("-" * 60)

    _check_credentials()

    from scheduler_service import start_scheduler
    
    # Start the Reservoir Scheduling Service (Background)
    logger.info("Initializing Reservoir Scheduling Service...")
    start_scheduler()
    
    # Keep main alive (Scheduler runs in a daemon thread)
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")


if __name__ == "__main__":
    main()
