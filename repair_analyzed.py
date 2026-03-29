import os
import json
import shutil
import logging
from analyzer import _is_junk_name, analyze_media, _sanitize_filename
import config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("repair")

def repair():
    analyzed_dir = config.ANALYZED_FOLDER
    if not os.path.exists(analyzed_dir):
        logger.error(f"Analyzed folder not found: {analyzed_dir}")
        return

    logger.info(f"Scanning {analyzed_dir} for junk names...")
    
    folders = [f for f in os.listdir(analyzed_dir) if os.path.isdir(os.path.join(analyzed_dir, f))]
    
    for folder_name in folders:
        if _is_junk_name(folder_name):
            logger.info(f"Found junk folder: {folder_name}")
            folder_path = os.path.join(analyzed_dir, folder_name)
            
            # Find the video file
            video_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp4', '.mov', '.avi', '.mkv'))]
            if not video_files:
                logger.warning(f"No video found in {folder_name}, skipping.")
                continue
            
            video_path = os.path.join(folder_path, video_files[0])
            
            logger.info(f"Re-analyzing: {video_path}")
            try:
                # This will use the improved fallback if AI fails
                result = analyze_media(video_path)
                
                new_folder_name = os.path.basename(result['output_folder'])
                if new_folder_name != folder_name:
                    logger.info(f"Successfully repaired to: {new_folder_name}")
                    # The analyze_media already moves files to a NEW folder.
                    # So we just need to delete the OLD folder if it's empty or has the old junk.
                    if os.path.exists(folder_path) and folder_path != result['output_folder']:
                         # If the old folder still exists, it might be because analyze_media created a new one
                         # instead of renaming. Let's clean up the old junk folder.
                         try:
                             shutil.rmtree(folder_path)
                             logger.info(f"Removed old junk folder: {folder_name}")
                         except Exception as e:
                             logger.error(f"Error removing old folder {folder_name}: {e}")
                else:
                    logger.warning(f"Analysis still resulted in same name for {folder_name}")
            except Exception as e:
                logger.error(f"Failed to repair {folder_name}: {e}")

if __name__ == "__main__":
    repair()
