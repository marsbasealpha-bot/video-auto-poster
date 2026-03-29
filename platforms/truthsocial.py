"""
platforms/truthsocial.py - Truth Social uploader using Playwright.
Truth Social is a Mastodon fork — uploads via the web interface.
"""
import os
import time
import logging
from playwright.sync_api import sync_playwright
import config

logger = logging.getLogger(__name__)


def upload(video_path: str, title: str, hashtags: str, description: str):
    """
    Uploads a video to Truth Social via browser automation.
    """
    if not config.ENABLE_TRUTHSOCIAL:
        logger.info("Truth Social platform is disabled. Skipping.")
        return

    session_file = getattr(config, "TRUTHSOCIAL_SESSION_FILE", "")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx_args = {}
        if session_file and os.path.exists(session_file):
            ctx_args["storage_state"] = session_file
        else:
            logger.warning(f"Truth Social session file not found: {session_file}")

        context = browser.new_context(**ctx_args)
        page = context.new_page()

        try:
            logger.info("Navigating to Truth Social...")
            page.goto("https://truthsocial.com/", wait_until="networkidle", timeout=30000)

            # Check if we need to log in
            if page.query_selector('input[name="email"], input[name="username"]'):
                username = getattr(config, "TRUTHSOCIAL_USERNAME", "")
                password = getattr(config, "TRUTHSOCIAL_PASSWORD", "")
                if username and password:
                    logger.info("Logging in to Truth Social...")
                    email_input = page.query_selector('input[name="email"], input[name="username"]')
                    if email_input:
                        email_input.fill(username)
                    pass_input = page.query_selector('input[name="password"]')
                    if pass_input:
                        pass_input.fill(password)
                    submit = page.query_selector('button[type="submit"]')
                    if submit:
                        submit.click()
                    page.wait_for_load_state("networkidle")
                    # Save session for next time
                    if session_file:
                        context.storage_state(path=session_file)
                        logger.info(f"Saved Truth Social session to: {session_file}")
                else:
                    raise RuntimeError("Truth Social login required but no credentials configured.")

            # Navigate to compose / post
            # Truth Social is Mastodon-based, look for compose button
            compose_btn = page.query_selector(
                'button[aria-label="Compose"], '
                'a[href="/compose"], '
                'button:has-text("Truth")'
            )
            if compose_btn:
                compose_btn.click()
                time.sleep(1)

            # Fill in the post text
            full_text = f"{title}\n\n{hashtags}"
            if description:
                full_text += f"\n\n{description}"

            text_area = page.query_selector(
                'textarea, '
                'div[contenteditable="true"], '
                'div[role="textbox"]'
            )
            if text_area:
                text_area.click()
                text_area.fill(full_text)

            # Upload the video
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(video_path)
                logger.info("Video file attached to Truth Social post.")
                # Wait for upload to complete
                time.sleep(5)
            else:
                # Try clicking the media button first
                media_btn = page.query_selector(
                    'button[aria-label="Upload media"], '
                    'button:has-text("Media")'
                )
                if media_btn:
                    media_btn.click()
                    time.sleep(1)
                    file_input = page.query_selector('input[type="file"]')
                    if file_input:
                        file_input.set_input_files(video_path)
                        time.sleep(5)

            # Submit the post
            post_btn = page.query_selector(
                'button:has-text("Truth"), '
                'button:has-text("Post"), '
                'button[type="submit"]'
            )
            if post_btn:
                post_btn.click()
                page.wait_for_load_state("networkidle", timeout=60000)
                logger.info("Successfully posted to Truth Social.")
            else:
                logger.warning("Could not find post button on Truth Social.")

        except Exception as e:
            logger.error(f"Error during Truth Social upload: {e}")
            raise
        finally:
            browser.close()
