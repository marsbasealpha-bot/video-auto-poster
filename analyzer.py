"""
analyzer.py - Standalone video/image analyzer using Google Gemini.
Analyzes media, generates metadata (title, description, hashtags, mentions,
thumbnail prompt), renames the file, and organizes into an output folder.
"""
import os
import sys
import gc
import json
import shutil
import time
import logging
import traceback
import base64
import requests
import random

# Fix for pythonw: sys.stderr/stdout are None, which crashes moviepy/tqdm
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')

from PIL import Image
try:
    try:
        from moviepy.editor import VideoFileClip
    except ImportError:
        from moviepy import VideoFileClip
except ImportError:
    # BEST PRACTICE: If MoviePy is missing entirely, we don't crash here.
    # The error will be caught during actual processing, allowing the GUI to show a clear 'Missing Dependency' msg.
    VideoFileClip = None
from google import genai
from google.genai import types
import config

logger = logging.getLogger(__name__)

def _sanitize_filename(name):
    """
    BEST PRACTICE: Filename Sanitization.
    Removes illegal Windows characters from AI-generated titles.
    """
    import re
    if not name: return "UNTITLED"
    # Remove \ / : * ? " < > |
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    # Strip leading/trailing whitespace and limit length
    return name.strip()[:100]

# Supported file types
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# Initialize the GenAI client
client = None
if config.GEMINI_API_KEY:
    client = genai.Client(api_key=config.GEMINI_API_KEY)


def analyze_media(file_path: str) -> dict:
    """
    Main entry point. Analyzes a video or image file with Gemini AI.

    Returns a dict with:
        title, description, hashtags, mentions, thumbnail_prompt,
        transcript, subtitles_srt, output_folder, output_path, metadata_path
    """
    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    is_video = ext in VIDEO_EXTS
    is_image = ext in IMAGE_EXTS

    if not is_video and not is_image:
        raise ValueError(f"Unsupported file type: {ext}")

    logger.info(f"Analyzing {'video' if is_video else 'image'}: {file_path}")

    # ── Step 1: Prepare Modal Parts (Image & Audio) ──
    image_data, image_mime = _get_image_data(file_path, is_video)
    audio_data, audio_mime = None, None
    if is_video:
        audio_data, audio_mime = _extract_audio(file_path)

    # ── Step 2: Call Gemini (Combined Metadata + Transcription) ──
    original_name = os.path.splitext(os.path.basename(file_path))[0]
    metadata = _call_gemini_multimodal(
        image_data, image_mime, 
        audio_data, audio_mime, 
        original_name
    )
    
    # ── Synergy Pass: Marketing Strategy ──
    try:
        import strategist
        import thumbnailer
        logger.info("Executing AI Synergy pass (Marketing Plan)...")
        refined = strategist.plan_metadata(metadata)
        # Update metadata with refined values while keeping files/transcript
        for key in ["title", "hook", "description", "hashtags", "mentions", "thumbnail_prompt"]:
            if refined.get(key):
                metadata[key] = refined[key]
        
        # ── Step 2.5: Generate Thumbnail ──
        if metadata.get("thumbnail_prompt"):
            # Prepare output folder for thumbnail
            hook_name = metadata.get("hook") or metadata.get("title") or original_name
            sanitized_name = _sanitize_filename(hook_name)
            output_dir = os.path.join(config.ANALYZED_FOLDER, sanitized_name)
            os.makedirs(output_dir, exist_ok=True)
            
            thumb_path = thumbnailer.generate_thumbnail(metadata["thumbnail_prompt"], output_dir)
            if thumb_path:
                metadata["thumbnail_path"] = thumb_path
                
    except Exception as e:
        logger.warning(f"Synergy/Thumbnail pass failed: {e}. Proceeding with raw analysis.")

    logger.info(f"Generated metadata: hook={metadata.get('hook', 'No Hook')}")

    # ── Step 3: Create output folder ──
    # User wants to rename based on the Hook
    hook_name = metadata.get("hook") or metadata.get("title") or original_name
    sanitized_name = _sanitize_filename(hook_name)
    
    output_folder = os.path.join(config.ANALYZED_FOLDER, sanitized_name)
    os.makedirs(output_folder, exist_ok=True)

    # ── Step 4: Rename and move the file ──
    new_name = f"{sanitized_name}{ext}"
    output_path = os.path.join(output_folder, new_name)

    # Handle name collision
    if os.path.exists(output_path):
        base = sanitized_name
        output_path = os.path.join(output_folder, f"{base}_{int(time.time())}{ext}")

    # Retry loop for Windows file-in-use
    for attempt in range(5):
        try:
            shutil.move(file_path, output_path)
            break
        except PermissionError:
            if attempt < 4:
                time.sleep(1.0)
            else:
                raise

    logger.info(f"Moved file to: {output_path}")

    # ── Step 5: Save metadata.json and subtitles.srt ──
    metadata["original_filename"] = os.path.basename(file_path)
    metadata["output_path"] = output_path
    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if metadata.get("subtitles_srt"):
        srt_path = os.path.join(output_folder, "subtitles.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(metadata["subtitles_srt"])
        logger.info(f"Saved subtitles to: {srt_path}")

    logger.info(f"Saved metadata to: {metadata_path}")

    # Return everything
    return {
        **metadata,
        "output_folder": output_folder,
        "output_path": output_path,
        "metadata_path": metadata_path,
    }


def _get_image_data(file_path: str, is_video: bool) -> tuple:
    """Extract image bytes for Gemini. For video, extracts a mid-point frame."""
    if is_video:
        frame_path = file_path + ".analysis_frame.jpg"
        try:
            clip = VideoFileClip(file_path)
            frame_time = min(2.0, clip.duration / 2)
            clip.save_frame(frame_path, t=frame_time)
            clip.close()
            del clip
            gc.collect()
            time.sleep(0.5)  # Let Windows release the file handle

            with open(frame_path, "rb") as f:
                data = f.read()

            # Clean up temp frame
            try:
                os.remove(frame_path)
            except Exception:
                pass

            return data, "image/jpeg"
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            raise
    else:
        # Image file — read directly
        with open(file_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".gif": "image/gif",
            ".bmp": "image/bmp", ".webp": "image/webp",
        }
        return data, mime_map.get(ext, "image/jpeg")


def _extract_audio(file_path: str) -> tuple:
    """Extract audio from video file to a temp mp3."""
    audio_path = file_path + ".analysis_audio.mp3"
    try:
        clip = VideoFileClip(file_path)
        if clip.audio is None:
            clip.close()
            return None, None
        
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()
        del clip
        gc.collect()
        
        with open(audio_path, "rb") as f:
            data = f.read()
            
        try:
            os.remove(audio_path)
        except Exception:
            pass
            
        return data, "audio/mpeg"
    except Exception as e:
        logger.error(f"Audio extraction failed: {e}")
        return None, None


def _call_gemini_multimodal(image_data: bytes, image_mime: str, 
                         audio_data: bytes = None, audio_mime: str = None, 
                         original_name: str = "") -> dict:
    """
    Single call to Gemini for both vision and audio analysis.
    Implements a fallback chain to handle 429 quota errors.
    """
    if not client:
        return _fallback_metadata(original_name)

    # Models to try in order. Primary is 2.0 Flash, followed by 1.5 Flash/Pro and 2.0 Lite.
    MODELS = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-pro-latest", "gemini-2.0-flash-lite"]
    
    # Check for existing metadata (Refinement logic)
    # NOTE: On first analysis, there is no output folder yet.
    # Feedback is only available on re-analysis (triggered from the Pilot Control).
    latest_feedback = ""

    from feedback_engine import get_lessons_prompt
    lessons_context = get_lessons_prompt()
    
    refinement_block = f"\n### TARGETED REFINEMENT REQUEST (MUST FOLLOW):\n\"{latest_feedback}\"\n" if latest_feedback else ""

    prompt = (
        "You are a social media expert and viral content strategist. "
        "Analyze this content (image frame and audio) and generate comprehensive metadata.\n\n"
        f"{lessons_context}\n"
        f"{refinement_block}\n"
        "Return ONLY valid JSON with these exact keys:\n"
        "{\n"
        '  "title": "A catchy title (max 60 chars)",\n'
        '  "hook": "A viral, attention-grabbing hook (max 100 chars)",\n'
        '  "description": "A compelling 2-3 sentence description",\n'
        '  "transcript": "Full plain text transcription",\n'
        '  "subtitles_srt": "Valid SRT formatted string with timestamps",\n'
        '  "hashtags": "#hashtag1 #hashtag2 ... #hashtag30",\n'
        '  "mentions": "@relevant_account1 @relevant_account2",\n'
        '  "thumbnail_prompt": "A detailed 100+ word AI image generation prompt",\n'
        '  "word_timestamps": [{"word": "the", "start": 0.5, "end": 0.8}, ...]\n'
        "}\n\n"
        "Requirements:\n"
        "- hook should be the most viral sentence from the video, used for the filename\n"
        "- Title must be bold, clickbait-worthy, and summarized from the content\n"
        "- Description should hook the viewer immediately\n"
        "- transcript should be as accurate as possible\n"
        "- subtitles_srt must follow strict SRT format\n"
        "- word_timestamps MUST BE EXTREMELY ACCURATE for word-by-word animation\n"
        "- Include 30 highly relevant hashtags (YouTube max)\n"
        "- thumbnail_prompt MUST be 100+ words, hyper-detailed, describing cinematic lighting, "
        "camera angles, textures, and one of these styles: Hyper-Real Close-up, Visual Split Layout, "
        "Object of Power, Maximum Contrast, or Hyper-Expressive.\n"
        "- Return ONLY the JSON, no markdown, no explanation."
    )

    parts = [prompt, types.Part.from_bytes(data=image_data, mime_type=image_mime)]
    if audio_data:
        parts.append(types.Part.from_bytes(data=audio_data, mime_type=audio_mime))

    last_error = None
    for model_name in MODELS:
        try:
            logger.info(f"Attempting analysis with model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=parts,
            )

            text = response.text.strip()
            # Handle potential markdown fencing
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            
            metadata = json.loads(text.strip())

            # Basic validation/fixup
            required = ["title", "hook", "description", "hashtags", "thumbnail_prompt"]
            fallback = _fallback_metadata(original_name)
            for key in required:
                if not metadata.get(key):
                    metadata[key] = fallback.get(key, "")
            
            return metadata

        except Exception as e:
            err_str = str(e).upper()
            last_error = e
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "QUOTA" in err_str:
                logger.warning(f"Model {model_name} hit quota/429. Trying next...")
                time.sleep(1) # Small breather
                continue
            else:
                # If it's not a quota error, it might be a content issue or auth; 
                # but we'll try the next model anyway just in case it's model-specific
                logger.error(f"Model {model_name} failed: {e}")
                continue

    logger.error(f"All models failed or hit quota. Last error: {last_error}")
    return _fallback_metadata(original_name)


def _call_grok_vision(image_data: bytes, image_mime: str, original_name: str) -> dict:
    """Fallback to Grok (xAI) for high-quality vision analysis."""
    logger.info("Attempting analysis with Grok (xAI)...")
    
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.GROK_API_KEY}"
    }
    
    # xAI Prompt
    system_prompt = (
        "You are a social media expert. Analyze the provided image and generate metadata. "
        "Return ONLY valid JSON with keys: title, hook, description, hashtags, mentions, thumbnail_prompt. "
        "Requirements: hook is a viral sentence (max 100 chars), title is clickbait, "
        "include 30 hashtags, and 100+ word thumbnail prompt."
    )
    
    payload = {
        "model": "grok-2-vision-1212", # Using a known stable vision model
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Analyze this content. Original filename: {original_name}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    
    result = response.json()
    text = result['choices'][0]['message']['content'].strip()
    
    # Handle markdown fencing
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
        
    metadata = json.loads(text.strip())
    
    # Ensure all required keys exist
    required = ["title", "hook", "description", "hashtags", "thumbnail_prompt"]
    fallback = _fallback_metadata(original_name)
    for key in required:
        if not metadata.get(key):
            metadata[key] = fallback.get(key, "")
            
    return metadata


FALLBACK_DESCRIPTIONS = [
    "You won't believe what happens next! Watch until the end. 😱",
    "This is absolutely insane! I wasn't expecting this at all. 🔥",
    "Wait for it... one of the craziest things I've seen lately! ✨",
    "The ending will leave you speechless. Tag a friend who needs to see this! 👇",
    "Can we just take a moment to appreciate how epic this is? 🚀",
    "Just when you thought you'd seen it all... watch this! 🤯",
    "This is purely for the vibes. Don't scroll past without a like! ❤️",
    "Is it just me or is this the most satisfying thing ever? 💎",
    "Proof that anything is possible if you just keep going. #Motivation",
    "I've watched this 10 times and I'm still confused. Thoughts? 💬",
    "This is why you never give up. Pure inspiration! 🌈",
    "The camera actually caught this! Unbelievable. 📸",
    "Daily dose of content you didn't know you needed. 💊",
    "Is this real life or is this just fantasy? 🌌",
    "I'm sending this to everyone I know. Spread the word! 📲"
]

FALLBACK_HOOKS = [
    "Wait for the end... 😱",
    "This is absolutely INSANE 🔥",
    "I wasn't expecting this! ✨",
    "The ending is speechless... 👇",
    "This is purely EPIC 🚀",
    "Watch this right now! 🤯",
    "Satisfying video of the day 💎",
    "You NEED to see this! ❤️",
    "Proof that anything is possible ✨",
    "I'm still confused... 💬",
    "Unbelievable captured! 📸",
    "The vibes are immaculate 🌈",
    "Don't scroll past this 📲",
    "Is this even real? 🌌",
    "Wait for the reveal... 🎭"
]


def _is_junk_name(name: str) -> bool:
    """Detect if a filename is generic junk (UUID, 'grok video', previous fallbacks, etc.)."""
    name_lower = name.lower().strip()
    if not name_lower or name_lower in ["untitled", "video", "output", "clip"]:
        return True
    if "grok video" in name_lower:
        return True
        
    # Check if it matches any of our own fallback hooks (case-insensitive)
    for hook in FALLBACK_HOOKS:
        hook_base = hook.replace("...", "").split("!")[0].split("?")[0].strip().lower()
        if hook_base and hook_base in name_lower and len(hook_base) > 5:
            return True
            
    # Check for UUID-like hex strings
    import re
    if re.search(r'[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}', name_lower):
        return True
    # Check for long random-looking strings or lots of spaces + numbers
    if len(re.findall(r'[0-9a-f]', name_lower)) > 15 and len(name.split()) > 4:
        return True
    return False


def _fallback_metadata(original_name: str = "") -> dict:
    """Fallback metadata when Gemini is unavailable."""
    clean_name = original_name.replace("_", " ").replace("-", " ").strip() if original_name else "Untitled"
    
    # If the filename is junk, don't use it for the title
    hook = random.choice(FALLBACK_HOOKS)
    title = clean_name
    if _is_junk_name(clean_name):
        title = hook.replace("...", "").replace("😱", "").replace("🔥", "").strip() or "Must Watch Video"

    return {
        "title": title,
        "hook": hook,
        "description": random.choice(FALLBACK_DESCRIPTIONS),
        "transcript": "",
        "subtitles_srt": "",
        "hashtags": "#viral #trending #fyp #mustsee #wow",
        "mentions": "",
        "thumbnail_prompt": "High-contrast cinematic shot with vibrant colors and dramatic lighting.",
    }


def _sanitize_filename(name: str, max_len: int = 60) -> str:
    """Sanitize a string for use as a filename on Windows."""
    # Remove restricted characters
    for char in '<>:"/\\|?*\r\n':
        name = name.replace(char, "")
    # Collapse whitespace
    name = " ".join(name.split())
    # Trim length
    name = name.strip()[:max_len].strip()
    return name if name else "Untitled"
