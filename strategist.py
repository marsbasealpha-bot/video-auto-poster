"""
strategist.py - AI Strategist for Video Auto-Poster.
Refines raw vision analysis into high-converting marketing metadata.
"""
import json
import logging
import requests
import time
from google import genai
import config

logger = logging.getLogger(__name__)

def plan_metadata(raw_analysis: dict) -> dict:
    """
    Takes raw analysis and uses Grok/Gemini to craft viral metadata.
    """
    context = (
        f"The following is a raw analysis of a media file:\n"
        f"Transcript: {raw_analysis.get('transcript', 'N/A')}\n"
        f"Visuals: {raw_analysis.get('description', 'N/A')}\n"
        f"Initial Hook: {raw_analysis.get('hook', 'N/A')}\n"
    )
    
    prompt = (
        "Based on this raw data, craft the ultimate viral marketing package for social media (Shorts/TikTok/Reels). "
        "Return ONLY valid JSON with these keys: title, hook, description, hashtags, mentions, thumbnail_prompt. "
        "Requirements:\n"
        "- Hook must be a calculated pattern-interrupt sentence for the filename.\n"
        "- Title must be psychologically optimized for clicks.\n"
        "- Description must follow a 'Hook -> Value -> CTA' structure.\n"
        "- Hashtags: 30 niche and viral tags.\n"
        "- Thumbnail Prompt: High-converting visual prompt (100+ words)."
    )
    
    res_text = generate_strategy(prompt, context)
    try:
        # Extract JSON from the strategist output
        if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0]
        return json.loads(res_text.strip())
    except Exception as e:
        logger.error(f"Failed to parse strategist metadata: {e}")
        return raw_analysis

def generate_strategy(prompt: str, context: str = "") -> str:
    if config.GROK_API_KEY:
        try:
            return _call_grok(prompt, context)
        except Exception as e:
            logger.warning(f"Grok failed, falling back to Gemini: {e}")
            
    return _call_gemini(prompt, context)

def _call_grok(prompt: str, context: str) -> str:
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.GROK_API_KEY}"
    }
    payload = {
        "model": "grok-2-1212",
        "messages": [
            {"role": "system", "content": "You are Marketing AI, a viral marketing strategist. Provide actionable, high-impact advice. " + context},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def _call_gemini(prompt: str, context: str) -> str:
    if not config.GEMINI_API_KEY:
        return "Error: No API keys configured."
        
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    full_prompt = f"System: You are Marketing AI, a viral marketing strategist. Context: {context}\n\nUser: {prompt}"
    response = client.models.generate_content(model="gemini-2.0-flash", contents=full_prompt)
    return response.text
