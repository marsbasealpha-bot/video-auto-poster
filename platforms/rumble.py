"""
platforms/rumble.py - Rumble uploader using Playwright.
Requires a saved session file from manual login.
"""
import os
import time
import logging
from playwright.sync_api import sync_playwright
import config

logger = logging.getLogger(__name__)


def upload(video_path: str, title: str, hashtags: str, description: str):
    """
    Uploads a video to Rumble via browser automation.
    """
    if not config.ENABLE_RUMBLE:
        logger.info("Rumble platform is disabled. Skipping.")
        return

    session_file = getattr(config, "RUMBLE_SESSION_FILE", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_args = {}
        if session_file and os.path.exists(session_file):
            ctx_args["storage_state"] = session_file
        else:
            logger.warning(f"Rumble session file not found: {session_file}")

        context = browser.new_context(**ctx_args)
        page = context.new_page()

        try:
            logger.info("Navigating to Rumble upload page...")
            page.goto("https://rumble.com/upload.php", wait_until="networkidle", timeout=30000)

            # Check if we need to log in
            if "login" in page.url.lower() or page.query_selector('input[name="username"]'):
                username = getattr(config, "RUMBLE_USERNAME", "")
                password = getattr(config, "RUMBLE_PASSWORD", "")
                if username and password:
                    logger.info("Logging in to Rumble...")
                    page.fill('input[name="username"]', username)
                    page.fill('input[name="password"]', password)
                    page.click('button[type="submit"]')
                    page.wait_for_load_state("networkidle")
                    # Save session for next time
                    if session_file:
                        context.storage_state(path=session_file)
                        logger.info(f"Saved Rumble session to: {session_file}")
                else:
                    raise RuntimeError("Rumble login required but no credentials configured.")

            # Upload the video file
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(video_path)
                logger.info("Video file selected for upload.")
            else:
                raise RuntimeError("Could not find file input on Rumble upload page.")

            # Wait for upload to process
            time.sleep(3)

            # Fill in metadata
            title_input = page.query_selector('input[name="title"], input#title')
            if title_input:
                title_input.fill(f"{title} {hashtags}")

            desc_input = page.query_selector('textarea[name="description"], textarea#description')
            if desc_input:
                full_desc = f"{description}\n\n{hashtags}" if description else hashtags
                desc_input.fill(full_desc)

            # Select category if available
            category_select = page.query_selector('select[name="category"]')
            if category_select:
                category_select.select_option(label="Entertainment")

            # Submit
            submit_btn = page.query_selector('button[type="submit"], input[type="submit"]')
            if submit_btn:
                submit_btn.click()
                page.wait_for_load_state("networkidle", timeout=60000)
                logger.info("Successfully uploaded to Rumble.")
            else:
                logger.warning("Could not find submit button on Rumble.")

        except Exception as e:
            logger.error(f"Error during Rumble upload: {e}")
            raise
        finally:
            browser.close()
