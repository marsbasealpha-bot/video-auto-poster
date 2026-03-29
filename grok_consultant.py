import os
import sys
import requests
import json
import dotenv

def consult_grok(query, file_path=None):
    """
    Sends a coding question or file to Grok (xAI) for analysis.
    """
    dotenv.load_dotenv()
    api_key = os.getenv("GROK_API_KEY")
    
    if not api_key:
        print("Error: GROK_API_KEY not found in .env")
        return

    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    content = query
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        content = f"{query}\n\n--- FILE CONTENT ({os.path.basename(file_path)}) ---\n{file_content}"

    payload = {
        "model": "grok-2-1212", # Using the stable December model
        "messages": [
            {"role": "system", "content": "You are a world-class software engineer and coding consultant. Provide concise, expert advice on the provided code or issue."},
            {"role": "user", "content": content}
        ],
        "temperature": 0
    }

    print(f"Consulting Grok regarding: {query[:50]}...")
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        print("\n=== GROK'S ANALYSIS ===\n")
        print(result['choices'][0]['message']['content'])
        print("\n=======================\n")
    except Exception as e:
        print(f"Error consulting Grok: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python grok_consultant.py 'Your question' [file_path]")
    else:
        q = sys.argv[1]
        f = sys.argv[2] if len(sys.argv) > 2 else None
        consult_grok(q, f)
