"""
captions.py - "Alex Hormozi" style caption generator for Video Auto-Poster.
Generates vibrant, animated, word-by-word captions using Pillow and MoviePy.
"""
import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont
try:
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
    except ImportError:
        from moviepy import ImageClip, CompositeVideoClip
except ImportError:
    ImageClip = CompositeVideoClip = None
import config

logger = logging.getLogger(__name__)

# Style Constants
FONT_SIZE = 70
FONT_COLOR = "#FFFFFF"     # White
HIGHLIGHT_COLOR = "#00FF00" # Vibrant Green (Hormozi Style)
OUTLINE_COLOR = "#000000"   # Black
OUTLINE_WIDTH = 4

def create_caption_clips(word_timestamps, video_width, video_height):
    """
    Creates a list of MoviePy ImageClips for the given word timestamps.
    """
    clips = []
    
    # Try to find a bold font
    font_paths = [
        "C:\\Windows\\Fonts\\arialbd.ttf",  # Arial Bold
        "C:\\Windows\\Fonts\\impact.ttf",   # Impact
        "C:\\Windows\\Fonts\\segoeuib.ttf"  # Segoe UI Bold
    ]
    font = None
    for p in font_paths:
        if os.path.exists(p):
            font = ImageFont.truetype(p, FONT_SIZE)
            break
    if not font:
        font = ImageFont.load_default()

    for item in word_timestamps:
        word = item.get("word", "").upper()
        start = item.get("start", 0)
        end = item.get("end", 0)
        duration = end - start
        
        if duration <= 0: continue

        # Create a transparent image for the word
        # We'll make it the size of the video width to center easily
        img = Image.new("RGBA", (video_width, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate text position (centered horizontally)
        # Use getbbox or getsize depending on Pillow version
        try:
            bbox = draw.textbbox((0, 0), word, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except AttributeError:
            w, h = draw.textsize(word, font=font)
            
        x = (video_width - w) // 2
        y = (200 - h) // 2
        
        # Draw Outline
        for ox in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
            for oy in range(-OUTLINE_WIDTH, OUTLINE_WIDTH + 1):
                draw.text((x + ox, y + oy), word, font=font, fill=OUTLINE_COLOR)
        
        # Draw Text (Randomly highlight some words yellow or green)
        color = FONT_COLOR
        if len(word) > 5 or "!" in word:
            color = HIGHLIGHT_COLOR # Use green for 'important' words
            
        draw.text((x, y), word, font=font, fill=color)
        
        # Create ImageClip in a temp folder
        temp_dir = os.path.join(os.path.dirname(__file__), "temp_captions")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"word_{start}.png")
        img.save(temp_path)
        
        clip = ImageClip(temp_path).set_start(start).set_duration(duration).set_position(("center", 0.65), relative=True)
        clips.append(clip)
        
    return clips

def apply_captions(video_clip, word_timestamps):
    """
    Overlays Alex-style captions onto a MoviePy video clip.
    """
    if not word_timestamps:
        return video_clip
        
    logger.info(f"Applying {len(word_timestamps)} word-by-word captions...")
    
    caption_clips = create_caption_clips(
        word_timestamps, 
        video_clip.w, 
        video_clip.h
    )
    
    # Return a CompositeVideoClip
    return CompositeVideoClip([video_clip] + caption_clips)
