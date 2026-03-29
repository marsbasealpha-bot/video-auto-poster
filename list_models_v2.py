import os
from google import genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing all available models...")
try:
    models = client.models.list()
    for m in models:
        print(f"Model Name: {m.name} | Display Name: {m.display_name}")
except Exception as e:
    print(f"Error listing models: {e}")
