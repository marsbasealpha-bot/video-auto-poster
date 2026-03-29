"""
platforms/youtube.py - YouTube Shorts uploader.
Uses the YouTube Data API v3 with OAuth2. 
Credentials: client_secret.json (OAuth2 app credentials from Google Cloud Console).
On first run, a browser window will open for you to authorize the app.
The token is then saved to YOUTUBE_TOKEN_FILE for reuse.
"""
import os
import logging
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_authenticated_service():
    creds = None
    token_file = config.YOUTUBE_TOKEN_FILE
    secret_file = config.YOUTUBE_CLIENT_SECRET

    if os.path.exists(token_file):
        with open(token_file, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing YouTube access token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(secret_file):
                raise FileNotFoundError(
                    f"YouTube client_secret file not found: {secret_file}\n"
                    "Download it from Google Cloud Console > APIs & Services > Credentials."
                )
            logger.info("Starting YouTube OAuth flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "wb") as f:
            pickle.dump(creds, f)
        logger.info(f"YouTube token saved to {token_file}")

    return build("youtube", "v3", credentials=creds)


def upload(video_path: str, title: str, hashtags: str, description: str):
    """Upload a video as a YouTube Short."""
    service = _get_authenticated_service()

    full_description = f"{description}\n\n{hashtags}".strip()

    body = {
        "snippet": {
            "title": title[:100],  # YouTube title limit
            "description": full_description[:5000],
            "tags": [tag.lstrip("#") for tag in hashtags.split() if tag.startswith("#")],
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/*", resumable=True)

    logger.info(f"Uploading '{title}' to YouTube Shorts...")
    request = service.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.debug(f"YouTube upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    logger.info(f"YouTube upload complete! Video ID: {video_id}")
    logger.info(f"URL: https://www.youtube.com/shorts/{video_id}")
