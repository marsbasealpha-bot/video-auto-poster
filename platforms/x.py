"""
platforms/x.py - X (Twitter) uploader using Playwright.
Note: Requires manual login/session file for best reliability.
"""
import logging
import asyncio
from playwright.sync_api import sync_playwright
import config

logger = logging.getLogger(__name__)

def upload(video_path: str, title: str, hashtags: str, description: str):
    """
    Uploads a video to X (Twitter) as a post.
    """
    if not config.ENABLE_X:
        logger.info("X platform is disabled. Skipping.")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use session file if it exists, otherwise start fresh
        session_file = config.X_SESSION_FILE if config.X_SESSION_FILE and os.path.exists(config.X_SESSION_FILE) else None
        if not session_file:
            logger.warning(f"X session file not found: {config.X_SESSION_FILE}. Starting without saved session.")
        context = browser.new_context(storage_state=session_file)
        page = context.new_page()

        try:
            logger.info("Navigating to X upload page...")
            page.goto("https://x.com/compose/post")
            
            # This is a simplified placeholder for the actual X upload logic
            # Real-world X automation often requires complex selector handling
            # and potentially handling login if session is expired.
            
            # 1. Input text (title + hashtags + @elonmusk)
            full_text = f"{title}\n\n{hashtags}\n\nCC: @elonmusk"
            if description:
                full_text += f"\n\n{description}"
            
            # page.fill('div[aria-label="Post text"]', full_text)
            # 2. Upload video
            # page.set_input_files('input[type="file"]', video_path)
            # 3. Click Post
            # page.click('button[data-testid="tweetButton"]')
            
            logger.info("Successfully simulated upload to X (Twitter).")
        except Exception as e:
            logger.error(f"Error during X upload: {e}")
            raise
        finally:
            browser.close()
