"""
scheduler_service.py - Background service for the Video Auto-Poster.
Cycles through the reservoir on a schedule and handles priority posting.
"""
import os
import time
import logging
import threading
from datetime import datetime, timedelta
import config
from queue_manager import QueueManager
from uploader import Uploader
import processor
import json

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.qm = QueueManager()
        self.uploader = Uploader()
        self.running = False
        self._thread = None
        self.last_post_time = 0
        self._load_state()

    def _load_state(self):
        """Load the last post time from a state file."""
        state_file = os.path.join(os.path.dirname(__file__), "scheduler_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    self.last_post_time = state.get("last_post_time", 0)
            except:
                pass

    def _save_state(self):
        """Save the last post time to a state file."""
        state_file = os.path.join(os.path.dirname(__file__), "scheduler_state.json")
        try:
            with open(state_file, "w") as f:
                json.dump({"last_post_time": self.last_post_time}, f)
        except:
            pass

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler Service started.")

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join()

    def _loop(self):
        while self.running:
            try:
                self._check_and_post()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
            
            # Check every minute
            time.sleep(60)

    def _check_and_post(self):
        queue = self.qm.load_queue()
        if not queue:
            return

        now = time.time()
        
        # 1. Check for IMMEDIATE PRIORITY
        # If config says priority should post immediately, and there is one
        priority_item = next((item for item in queue if item['priority'] and item['status'] == 'queued'), None)
        
        if priority_item and config.PRIORITY_POST_IMMEDIATE:
            logger.info(f"Priority item detected: {priority_item['filename']}. Posting immediately.")
            self._execute_post(priority_item)
            return

        # 2. Check REGULAR SCHEDULE
        # If it's been long enough since the last post
        interval_seconds = config.SCHEDULING_INTERVAL_HOURS * 3600
        next_post_time = self.last_post_time + interval_seconds
        
        if now >= next_post_time:
            next_item = self.qm.get_next_queued()
            if next_item:
                logger.info(f"Scheduled posting time reached for: {next_item['filename']}")
                self._execute_post(next_item)

    def _execute_post(self, item):
        """Process and upload a queued item using a stage-gate pipeline."""
        video_path = item['path']
        filename = item['filename']
        stage = item.get("current_stage", "analysis")
        
        try:
            logger.info(f"--- Pipeline Stage [{stage.upper()}]: {filename} ---")
            
            # --- STAGE 1: ANALYSIS (Done at Ingestion, but we finalize here) ---
            if stage == "analysis":
                self.qm.update_status(video_path, "processing")
                # Analysis is done by WatchWindow during ingest. 
                # We check the gate now.
                if config.CONFIRM_METADATA:
                    logger.info(f"Pausing for METADATA approval: {filename}")
                    self.qm.update_stage(filename, "captioning", "pending")
                    return
                stage = "captioning"

            # --- STAGE 2: CAPTIONING (PROCESSOR) ---
            if stage == "captioning":
                self.qm.update_status(video_path, "processing")
                
                # Load metadata for timestamps
                meta_path = os.path.join(os.path.dirname(video_path), "metadata.json")
                word_timestamps = None
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        word_timestamps = meta.get("word_timestamps")
                
                # Run the processor (Alex Style)
                processed_path = processor.process_video(video_path, word_timestamps=word_timestamps)
                # Store the processed path in queue for next stage
                self.qm.update_path(filename, processed_path)
                
                if config.CONFIRM_CAPTIONS:
                    logger.info(f"Pausing for CAPTION approval: {filename}")
                    self.qm.update_stage(filename, "rendering", "pending")
                    return
                stage = "rendering"

            # --- STAGE 3: RENDERING (FINAL CHECK) ---
            if stage == "rendering":
                self.qm.update_status(video_path, "processing")
                # Currently processing involves captions + concat in one go.
                # In the future, we might add a final quality check here.
                if config.CONFIRM_FINAL:
                    logger.info(f"Pausing for FINAL QUALITY approval: {filename}")
                    self.qm.update_stage(filename, "uploading", "pending")
                    return
                stage = "uploading"

            # --- STAGE 4: UPLOADING ---
            if stage == "uploading":
                self.qm.update_status(video_path, "uploading")
                
                # Load full metadata for upload
                meta_path = os.path.join(os.path.dirname(video_path), "metadata.json")
                title, hashtags, description = config.DEFAULT_TITLE, config.DEFAULT_HASHTAGS, ""
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        title = meta.get("title", title)
                        hashtags = meta.get("hashtags", hashtags)
                        description = meta.get("description", description)

                self.uploader.upload_all(
                    video_path, # This is the processed path now
                    title=title,
                    hashtags=hashtags,
                    description=description
                )
                
                # Finalize
                self.last_post_time = time.time()
                self._save_state()
                self.qm.update_status(video_path, "posted")
                
                # Move processed video to the final processed folder
                final_name = os.path.basename(video_path).replace("PROCESSED_", "")
                final_dest = os.path.join(config.PROCESSED_FOLDER, final_name)
                os.makedirs(config.PROCESSED_FOLDER, exist_ok=True)
                if os.path.exists(final_dest):
                    os.remove(final_dest)
                os.rename(video_path, final_dest)
                
                logger.info(f"--- Post Successful: {filename} ---")
            
        except Exception as e:
            logger.error(f"Failed pipeline at {stage}: {filename}: {e}", exc_info=True)
            self.qm.update_status(video_path, "failed")

def start_scheduler():
    service = SchedulerService()
    service.start()
    return service
