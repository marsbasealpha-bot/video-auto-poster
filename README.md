# Video Auto-Poster

Automatically post videos to **YouTube Shorts**, **TikTok**, and **Instagram Reels** by simply dropping a file into a folder.

## How It Works

1. Drop any video file into `C:\Users\Admin\Desktop\Uploads`
2. The script detects it, converts it to **1080x1920 (9:16)** using FFmpeg.
3. It uploads to all enabled platforms with randomized human-like delays.
4. The original file is moved to a `processed/` subfolder automatically.

**Tip:** Name your video like `My Cool Title #fyp #viral.mp4` to set the title and hashtags automatically.

---

## Setup

### 1. Prerequisites

- **Python 3.10+**
- **FFmpeg** installed and on your system PATH ([download here](https://ffmpeg.org/download.html))

### 2. Create & Activate Virtual Environment

```powershell
cd C:\Users\Admin\Desktop\video-auto-poster
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Install Playwright Browser

```powershell
playwright install chromium
```

### 4. Configure Credentials

Copy `.env.example` to `.env` and fill in your details:

```powershell
Copy-Item .env.example .env
notepad .env
```

### 5. One-Time Authentication Per Platform

#### YouTube

- Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
- Create an **OAuth 2.0 Client ID** (Desktop App) and download `client_secret.json` into this folder.
- On first run, a browser window will open for you to authorize the app. The token is then saved automatically.

#### TikTok

- Run the following to open a browser and log in manually:

```powershell
python -c "from tiktok_uploader.auth import AuthBackend; AuthBackend(cookies='tiktok_session.json').authenticate()"
```

#### Instagram

- Just set `INSTAGRAM_USERNAME` and `INSTAGRAM_PASSWORD` in `.env`.
- On first run, it logs in and saves the session automatically.

---

## Running the Service

```powershell
.\venv\Scripts\activate
python main.py
```

Leave the terminal open. Drop videos into the uploads folder anytime.

---

## File Structure

```
video-auto-poster/
├── main.py             # Entry point
├── config.py           # Configuration (reads .env)
├── watcher.py          # Folder monitoring (watchdog)
├── processor.py        # FFmpeg video processing
├── scheduler.py        # Human-like delay logic
├── uploader.py         # Upload orchestrator
├── platforms/
│   ├── youtube.py      # YouTube Shorts uploader
│   ├── tiktok.py       # TikTok uploader
│   └── instagram.py    # Instagram Reels uploader
├── requirements.txt
├── .env.example        # Credential template
└── README.md
```

## Logs

Logs are written to `video_auto_poster.log` in the project folder and also printed to the terminal.
