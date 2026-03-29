import os
from google import genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Listing Models...")
for m in client.models.list():
    if 'image' in m.name.lower() or 'gen' in m.name.lower():
        print(f"Name: {m.name}")
        print(f"Supported Methods: {m.supported_generation_methods}")
        print(f"Display Name: {m.display_name}")
        print("-" * 20)
