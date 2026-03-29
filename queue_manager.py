"""
queue_manager.py - Persistent queue management for the Video Auto-Poster.
Handles JSON storage, priority logic, and queue status.
"""
import os
import json
import time
import logging
from threading import Lock
import config

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.lock = Lock()
        self.queue_file = config.QUEUE_FILE
        self._ensure_queue_exists()

    def _ensure_queue_exists(self):
        if not os.path.exists(self.queue_file):
            self.save_queue([])

    def load_queue(self):
        with self.lock:
            try:
                if not os.path.exists(self.queue_file):
                    return []
                with open(self.queue_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load queue: {e}")
                return []

    def save_queue(self, queue_data):
        with self.lock:
            try:
                with open(self.queue_file, "w", encoding="utf-8") as f:
                    json.dump(queue_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save queue: {e}")

    def add_to_queue(self, file_path, priority=False):
        """Add a video to the queue. Priority items go to the front."""
        queue = self.load_queue()
        
        # Check if already in queue
        if any(item['path'] == file_path for item in queue):
            logger.info(f"File already in queue: {file_path}")
            return False

        item = {
            "path": file_path,
            "filename": os.path.basename(file_path),
            "priority": priority,
            "status": "queued",
            "current_stage": "analysis",
            "added_at": time.time(),
            "scheduled_at": None,
            "platforms": self._get_enabled_platforms()
        }

        # Estimate schedule based on previous items
        interval = config.SCHEDULING_INTERVAL_HOURS * 3600
        if priority:
            item["scheduled_at"] = time.time() # Priority is 'now' or next slot
            # Insert after the currently processing item (if any) or at the top
            insert_idx = 0
            for i, existing in enumerate(queue):
                if existing['status'] == 'processing':
                    insert_idx = i + 1
                    break
            queue.insert(insert_idx, item)
            logger.info(f"Added PRIORITY item to queue: {item['filename']}")
        else:
            last_scheduled = time.time()
            for existing in reversed(queue):
                if existing.get("scheduled_at"):
                    last_scheduled = max(last_scheduled, existing["scheduled_at"])
                    break
            item["scheduled_at"] = last_scheduled + interval
            queue.append(item)
            logger.info(f"Added item to queue: {item['filename']}")

        self.save_queue(queue)
        return True

    def _get_enabled_platforms(self):
        """Returns a string of enabled platforms for UI display."""
        enabled = []
        if config.ENABLE_YOUTUBE: enabled.append("YT")
        if config.ENABLE_TIKTOK: enabled.append("TT")
        if config.ENABLE_INSTAGRAM: enabled.append("IG")
        if config.ENABLE_X: enabled.append("X")
        return ", ".join(enabled)

    def update_stage(self, filename, stage, status="pending"):
        """Update the current processing stage and status of an item."""
        queue = self.load_queue()
        for item in queue:
            if item["filename"] == filename:
                item["current_stage"] = stage
                item["status"] = status
                break
        self.save_queue(queue)

    def update_path(self, filename, new_path):
        """Update the physical path of an item (e.g., after processing)."""
        queue = self.load_queue()
        for item in queue:
            if item["filename"] == filename:
                item["path"] = new_path
                break
        self.save_queue(queue)

    def mark_stage_approved(self, filename):
        """Moves an item from 'pending' to 'queued' for the next stage."""
        queue = self.load_queue()
        for item in queue:
            if item["filename"] == filename:
                item["status"] = "queued"
                # The scheduler will pick it up and move to next stage
                break
        self.save_queue(queue)

    def get_pending_counts(self):
        """Returns counts of items stuck at approval gates."""
        queue = self.load_queue()
        counts = {"metadata": 0, "captions": 0, "final": 0}
        for item in queue:
            if item["status"] == "pending":
                if item["current_stage"] == "analysis": counts["metadata"] += 1
                elif item["current_stage"] == "captioning": counts["captions"] += 1
                elif item["current_stage"] == "rendering": counts["final"] += 1
        return counts
        """Get the next item that should be processed."""
        queue = self.load_queue()
        for item in queue:
            if item['status'] == 'queued':
                return item
        return None

    def update_status(self, file_path, status):
        """Update the status of a specific item."""
        queue = self.load_queue()
        updated = False
        for item in queue:
            if item['path'] == file_path:
                item['status'] = status
                updated = True
                break
        if updated:
            self.save_queue(queue)
        return updated

    def remove_from_queue(self, file_path):
        """Remove an item from the queue."""
        queue = self.load_queue()
        new_queue = [item for item in queue if item['path'] != file_path]
        if len(new_queue) != len(queue):
            self.save_queue(new_queue)
            return True
        return False

    def clean_finished(self):
        """Remove items that are posted or failed."""
        queue = self.load_queue()
        new_queue = [item for item in queue if item['status'] not in ['posted', 'failed']]
        if len(new_queue) != len(queue):
            self.save_queue(new_queue)
