"""
processor.py - Video processing using MoviePy and FFmpeg.
Handles concatenation of Thumbnail (1s) + Random Intro + Main Video + Random Outro.
"""
import os
import sys
import random
import logging
import tempfile

# ─── Fix for pythonw: sys.stderr/stdout are None, which crashes moviepy/tqdm ───
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')

# ─── PIL Compatibility Shim ──────────────────────────────────────────────────
# MoviePy 1.0.3 references Image.ANTIALIAS which was removed in Pillow 10+.
# Restore it as an alias for Image.LANCZOS before moviepy imports PIL.
from PIL import Image
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS
# ─────────────────────────────────────────────────────────────────────────────

try:
    try:
        from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
    except ImportError:
        from moviepy import VideoFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
except ImportError:
    # Handle missing installations gracefully
    VideoFileClip = ImageClip = concatenate_videoclips = CompositeVideoClip = None
import config
import captions

# Set ImageMagick path if needed (for text, but we use Pillow in analyzer)
# from moviepy.config import change_settings
# change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick...\magick.exe"})

logger = logging.getLogger(__name__)

def process_video(main_video_path: str, word_timestamps=None) -> str:
    """
    Concatenates [Random Intro] + [Main Video] + [Random Outro].
    Returns the final video path.
    """
    logger.info(f"Starting advanced video processing: {main_video_path}")
    
    clips = []
    
    try:
        # 1. Random Intro
        intro_file = _get_random_file(config.INTRO_FOLDER)
        if intro_file:
            logger.info(f"Adding intro: {intro_file}")
            clips.append(VideoFileClip(intro_file))
            
        # 2. Main Video
        main_clip = VideoFileClip(main_video_path)
        clips.append(main_clip)
        
        # 3. Random Outro
        outro_file = _get_random_file(config.OUTRO_FOLDER)
        if outro_file:
            logger.info(f"Adding outro: {outro_file}")
            clips.append(VideoFileClip(outro_file))
            
        # Final Concatenation
        logger.info(f"Concatenating {len(clips)} segments...")
        final_clip = concatenate_videoclips(clips, method="compose")
        
        # 4. Apply Alex-style Captions if word_timestamps provided
        if word_timestamps:
            final_clip = captions.apply_captions(final_clip, word_timestamps)
        
        # Ensure final output is exactly target dimensions
        final_clip = final_clip.resize(lambda t: (config.TARGET_WIDTH, config.TARGET_HEIGHT))
        
        # Output to temp file
        ext = os.path.splitext(main_video_path)[1] or ".mp4"
        output_path = os.path.join(os.path.dirname(main_video_path), "PROCESSED_" + os.path.basename(main_video_path))
        
        final_clip.write_videofile(
            output_path,
            fps=config.TARGET_FPS,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=4,
            logger=None  # Suppress tqdm/proglog output (crashes under pythonw)
        )
        
        # Close all clips to release files
        for c in clips:
            c.close()
        final_clip.close()
        
        logger.info(f"Video processing finished: {output_path}")
        
        # Cleanup input file once processed
        _safe_cleanup(main_video_path)
            
        # Cleanup temp captions
        import shutil
        temp_dir = os.path.join(os.path.dirname(__file__), "temp_captions")
        if os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except: pass
            
        return output_path
        
    except Exception as e:
        logger.error(f"Advanced processing failed: {e}")
        # Clean up partial work
        for c in clips:
            try: c.close()
            except: pass
        raise

def _get_random_file(folder: str) -> str:
    """Picks a random video file from the specified folder."""
    if not os.path.exists(folder):
        return None
    files = [os.path.join(folder, f) for f in os.listdir(folder) 
             if f.lower().endswith(('.mp4', '.mov', '.mkv'))]
    return random.choice(files) if files else None

def _safe_cleanup(path: str):
    """Safely removes a file if it exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Cleaned up intermediate file: {path}")
    except Exception as e:
        logger.warning(f"Failed to clean up {path}: {e}")
