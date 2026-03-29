"""
config.py - Configuration and credential management.
Reads from a .env file in the project root.
"""
import os
import sys

# ─── MoviePy 2.x Compatibility Shim ──────────────────────────────────────────
# MoviePy 2.0+ removed the 'editor' submodule. Many dependencies (instagrapi, etc.)
# still try to import from it. We monkeypatch sys.modules to fix this globally.
try:
    import moviepy.editor
except ImportError:
    try:
        import moviepy
        sys.modules['moviepy.editor'] = moviepy
    except ImportError:
        pass # moviepy not installed at all
# ─────────────────────────────────────────────────────────────────────────────

from dotenv import load_dotenv

load_dotenv()

# ─── Folders ──────────────────────────────────────────────────────────────────
WATCH_FOLDER     = os.getenv("WATCH_FOLDER",     r"D:\Video Auto-Poster")
PROCESSED_FOLDER = os.getenv("PROCESSED_FOLDER", os.path.join(WATCH_FOLDER, "processed"))
ATTENTION_FOLDER = os.getenv("ATTENTION_FOLDER", os.path.join(WATCH_FOLDER, "attention"))
ANALYZED_FOLDER  = os.getenv("ANALYZED_FOLDER",  os.path.join(WATCH_FOLDER, "analyzed"))
ANALYZER_INBOX   = os.getenv("ANALYZER_INBOX",   os.path.join(WATCH_FOLDER, "analyzer_inbox"))
WATERMARK_FOLDER = os.getenv("WATERMARK_FOLDER", "")
INTRO_FOLDER     = os.getenv("INTRO_FOLDER",     os.path.join(WATCH_FOLDER, "intros"))
OUTRO_FOLDER     = os.getenv("OUTRO_FOLDER",     os.path.join(WATCH_FOLDER, "outros"))
INPUT_FOLDER     = os.getenv("INPUT_FOLDER",      "")
QUEUE_FILE       = os.getenv("QUEUE_FILE",       os.path.join(os.path.dirname(__file__), "queue.json"))

# ─── FFmpeg ───────────────────────────────────────────────────────────────────
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")  # must be on PATH or full path

# ─── Output Video Format (for Shorts / Reels / TikTok) ───────────────────────
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30

# ─── Scheduler ───────────────────────────────────────────────────────────────
# Random delay range (seconds) between each platform upload to look human-like
POST_DELAY_MIN = 300   # 5 minutes
POST_DELAY_MAX = 1800  # 30 minutes

# Reservoir Scheduling
SCHEDULING_INTERVAL_HOURS = int(os.getenv("SCHEDULING_INTERVAL_HOURS", "4"))
PRIORITY_POST_IMMEDIATE = os.getenv("PRIORITY_POST_IMMEDIATE", "true").lower() == "true"

# Stage Gates (Manual Approval)
CONFIRM_METADATA = os.getenv("CONFIRM_METADATA", "true").lower() == "true"
CONFIRM_CAPTIONS = os.getenv("CONFIRM_CAPTIONS", "true").lower() == "true"
CONFIRM_FINAL    = os.getenv("CONFIRM_FINAL",    "true").lower() == "true"

# ─── Platforms to Upload To ──────────────────────────────────────────────────
# Set to True/False to enable/disable each platform
ENABLE_YOUTUBE      = os.getenv("ENABLE_YOUTUBE",      "true").lower()  == "true"
ENABLE_TIKTOK       = os.getenv("ENABLE_TIKTOK",       "true").lower()  == "true"
ENABLE_INSTAGRAM    = os.getenv("ENABLE_INSTAGRAM",    "true").lower()  == "true"
ENABLE_X            = os.getenv("ENABLE_X",            "true").lower()  == "true"
ENABLE_RUMBLE       = os.getenv("ENABLE_RUMBLE",       "true").lower()  == "true"
ENABLE_TRUTHSOCIAL  = os.getenv("ENABLE_TRUTHSOCIAL",  "true").lower()  == "true"

# ─── AI Automation (Gemini & Grok) ─────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROK_API_KEY   = os.getenv("GROK_API_KEY", "")

# ─── YouTube ─────────────────────────────────────────────────────────────────
YOUTUBE_CHANNEL_ID     = os.getenv("YOUTUBE_CHANNEL_ID", "")
YOUTUBE_CLIENT_SECRET  = os.getenv("YOUTUBE_CLIENT_SECRET", "")  # path to client_secret.json
YOUTUBE_TOKEN_FILE     = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")

# ─── TikTok ──────────────────────────────────────────────────────────────────
TIKTOK_SESSION_FILE    = os.getenv("TIKTOK_SESSION_FILE", "tiktok_session.json")

# ─── Instagram ───────────────────────────────────────────────────────────────
INSTAGRAM_USERNAME     = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD     = os.getenv("INSTAGRAM_PASSWORD", "")
INSTAGRAM_SESSION_FILE = os.getenv("INSTAGRAM_SESSION_FILE", "instagram_session.json")

# ─── X (Twitter) ─────────────────────────────────────────────────────────────
X_USERNAME             = os.getenv("X_USERNAME", "")
X_PASSWORD             = os.getenv("X_PASSWORD", "")
X_SESSION_FILE         = os.getenv("X_SESSION_FILE", "x_session.json")

# ─── Rumble ───────────────────────────────────────────────────────────────────
RUMBLE_USERNAME        = os.getenv("RUMBLE_USERNAME", "")
RUMBLE_PASSWORD        = os.getenv("RUMBLE_PASSWORD", "")
RUMBLE_SESSION_FILE    = os.getenv("RUMBLE_SESSION_FILE", "rumble_session.json")

# ─── Truth Social ────────────────────────────────────────────────────────────
TRUTHSOCIAL_USERNAME      = os.getenv("TRUTHSOCIAL_USERNAME", "")
TRUTHSOCIAL_PASSWORD      = os.getenv("TRUTHSOCIAL_PASSWORD", "")
TRUTHSOCIAL_SESSION_FILE  = os.getenv("TRUTHSOCIAL_SESSION_FILE", "truthsocial_session.json")

# ─── Default Post Metadata ────────────────────────────────────────────────────
DEFAULT_TITLE      = os.getenv("DEFAULT_TITLE", "Check this out!")
DEFAULT_HASHTAGS   = os.getenv("DEFAULT_HASHTAGS", "#viral #trending #fyp @elonmusk")
DEFAULT_DESCRIPTION = os.getenv("DEFAULT_DESCRIPTION", "")
