"""
story_processor.py - LOCAL VERSION (Zero Token)
Enhanced with Best Practices: Logging, Automated Watching, and Error Handling.
"""
import os
import time
import shutil
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import WATCH_FOLDER

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("story_processor.log"),
        logging.StreamHandler()
    ]
)

class AIOutputHandler(FileSystemEventHandler):
    """
    Automated Folder Watcher: Monitors your AI render folder 
    and automatically moves files to the Auto-Poster inbox.
    """
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.mp4', '.mov')):
            logging.info(f"New AI render detected: {event.src_path}")
            self.process_video(event.src_path)

    def process_video(self, source_path):
        target_filename = f"Story_Video_{int(time.time())}.mp4"
        target_path = os.path.join(WATCH_FOLDER, target_filename)
        
        try:
            # Best Practice: Use shutil.move for efficiency, fall back to copy+delete
            shutil.copy2(source_path, target_path)
            logging.info(f"Successfully moved to Auto-Poster: {target_path}")
        except Exception as e:
            logging.error(f"Critical error moving file {source_path}: {e}")

def run_automated_watcher(directory_to_watch):
    """Starts the background directory watcher."""
    if not os.path.exists(directory_to_watch):
        logging.error(f"Directory not found: {directory_to_watch}")
        return

    event_handler = AIOutputHandler()
    observer = Observer()
    observer.schedule(event_handler, directory_to_watch, recursive=False)
    
    logging.info(f"--- Zero-Token Story Processor Active ---")
    logging.info(f"Watching for new renders in: {directory_to_watch}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Watcher stopped by user.")
    observer.join()

if __name__ == "__main__":
    import sys
    
    # Check for CLI arguments or prompt user
    if len(sys.argv) > 1:
        watch_path = sys.argv[1]
    else:
        print("Best Practice: Run this with a path to watch, e.g.: python story_processor.py \"C:\\Path\\To\\AI\\Output\"")
        watch_path = input("Enter the folder path where your AI (ComfyUI) saves videos: ").strip('"')

    if watch_path:
        run_automated_watcher(watch_path)
    else:
        logging.warning("No path provided. Script exiting.")
