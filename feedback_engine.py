"""
feedback_engine.py - Global AI Lessons Engine for Video Auto-Poster.
Manages a persistent lessons.json file to train the AI over time based on user feedback.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

LESSONS_FILE = os.path.join(os.path.dirname(__file__), "lessons.json")

def log_lesson(user_feedback, original_output, stage="analysis"):
    """
    Saves a new lesson to the global lessons list.
    """
    lessons = get_all_lessons()
    
    lesson = {
        "timestamp": datetime.now().isoformat(),
        "stage": stage,
        "user_feedback": user_feedback,
        "original_output_summary": str(original_output)[:200] + "..." if original_output else ""
    }
    
    lessons.append(lesson)
    
    # Prune lessons if it gets too long (keep last 50 for context)
    if len(lessons) > 50:
        lessons = lessons[-50:]
        
    try:
        with open(LESSONS_FILE, "w", encoding="utf-8") as f:
            json.dump(lessons, f, indent=2, ensure_ascii=False)
        logger.info(f"Loggd global lesson: {user_feedback}")
    except Exception as e:
        logger.error(f"Failed to save lesson: {e}")

def get_all_lessons():
    """Returns a list of all lessons from the JSON file."""
    if not os.path.exists(LESSONS_FILE):
        return []
    try:
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def get_lessons_prompt():
    """
    Formats the lessons into a string for the AI system prompt.
    """
    lessons = get_all_lessons()
    if not lessons:
        return ""
    
    prompt = "\n### LESSONS FROM PREVIOUS SESSIONS (DO NOT REPEAT THESE MISTAKES):\n"
    for i, lesson in enumerate(lessons[-10:]): # Only give last 10 lessons for context
        prompt += f"{i+1}. User Feedback: \"{lesson['user_feedback']}\"\n"
    
    prompt += "\nIncorporate these lessons into your strategy for this video.\n"
    return prompt
