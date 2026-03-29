"""
watcher.py - File system watcher using the watchdog library.
Monitors a folder for new video files and triggers the upload pipeline.
"""
import os
import time
import logging
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import config
import processor
from uploader import Uploader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


class VideoHandler(FileSystemEventHandler):
    """Handles new file creation events in the watch folder."""

    def __init__(self):
        super().__init__()
        self._processing = set()
        self._last_seen = {}  # path -> timestamp for debounce
        self._lock = threading.Lock()
        self.uploader = Uploader()

    def on_created(self, event):
        if event.is_directory:
            return

        path = event.src_path
        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.debug(f"Ignoring non-video file: {path}")
            return

        with self._lock:
            if path in self._processing:
                return
            # Debounce: ignore if same file seen within 5 seconds
            now = time.time()
            if path in self._last_seen and (now - self._last_seen[path]) < 5.0:
                return
            self._last_seen[path] = now
            self._processing.add(path)

        # Run in a thread to avoid blocking the observer
        thread = threading.Thread(target=self._handle_video, args=(path,), daemon=True)
        thread.start()

    def _handle_video(self, video_path: str):
        """Analyzes the video and adds it to the persistent queue for scheduling."""
        original_path = video_path
        try:
            # 0. Wait for the file to finish writing
            self._wait_for_file(video_path)
            logger.info(f"New video detected: {video_path}")

            # 1. Analyze and Move to 'analyzed/' reservoir immediately
            # This ensures metadata is ready for the Portal UI
            from analyzer import analyze_media
            from queue_manager import QueueManager
            
            self._update_status(f"Analyzing {os.path.basename(video_path)}...")
            result = analyze_media(video_path)
            
            analyzed_path = result.get("output_path")
            if not analyzed_path:
                logger.error(f"Analysis failed for {video_path}")
                return

            # 2. Add to Persistent Queue as PRIORITY
            qm = QueueManager()
            qm.add_to_queue(analyzed_path, priority=True)
            
            logger.info(f"Added {os.path.basename(analyzed_path)} to PRIORITY queue.")
            self._update_status(f"Added to Priority Queue: {os.path.basename(analyzed_path)}")

        except Exception as e:
            logger.error(f"Error handling video {video_path}: {e}", exc_info=True)
        finally:
            with self._lock:
                self._processing.discard(original_path)

    def _update_status(self, msg):
        """Try to update the watch window status if it exists."""
        try:
            # This is a bit of a hack to talk to the GUI if it's running in same process,
            # but usually they are separate. We'll rely on queue.json mostly.
            pass
        except:
            pass

    def _wait_for_file(self, path: str, stable_seconds: float = 2.0, timeout: float = 120.0):
        """Wait until file size stops changing (i.e., the file is fully written)."""
        elapsed = 0.0
        last_size = -1
        while elapsed < timeout:
            try:
                size = os.path.getsize(path)
            except OSError:
                time.sleep(0.5)
                elapsed += 0.5
                continue

            if size == last_size:
                return  # File is stable
            last_size = size
            time.sleep(stable_seconds)
            elapsed += stable_seconds

        raise TimeoutError(f"File {path} did not stabilize within {timeout}s")

    def _move_to_processed(self, path: str):
        os.makedirs(config.PROCESSED_FOLDER, exist_ok=True)
        basename = os.path.basename(path)
        dest = os.path.join(config.PROCESSED_FOLDER, basename)
        # Avoid overwrite
        if os.path.exists(dest):
            name, ext = os.path.splitext(basename)
            dest = os.path.join(config.PROCESSED_FOLDER, f"{name}_done{ext}")
        os.rename(path, dest)
        logger.info(f"Moved processed original to: {dest}")


def start_watching():
    """Start the file system observer. Blocks until interrupted."""
    os.makedirs(config.WATCH_FOLDER, exist_ok=True)
    logger.info(f"Watching folder: {config.WATCH_FOLDER}")

    handler = VideoHandler()
    observer = Observer()
    observer.schedule(handler, config.WATCH_FOLDER, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()
    observer.join()
