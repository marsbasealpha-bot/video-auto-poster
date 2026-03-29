import os
import logging
import sys
from google import genai
import dotenv

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import thumbnailer

logging.basicConfig(level=logging.INFO)

def test_gen():
    print("--- Diagnostic: Thumbnail Generation ---")
    prompt = "A high-quality cinematic thumbnail for a viral video about a Big Mac, dramatic lighting, high contrast."
    output_dir = os.path.join(config.ANALYZED_FOLDER, "test_diag")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Using Gemini API Key: {config.GEMINI_API_KEY[:10]}...")
    print(f"Target Directory: {output_dir}")
    
    path = thumbnailer.generate_thumbnail(prompt, output_dir)
    if path and os.path.exists(path):
        print(f"SUCCESS: Thumbnail created at {path}")
    else:
        print("FAILURE: Thumbnail not created. Check logs above.")

if __name__ == "__main__":
    test_gen()
