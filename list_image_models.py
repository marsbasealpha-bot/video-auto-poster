import os
from google import genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("Models with Image Generation Support:")
for m in client.models.list():
    if 'generate_images' in m.supported_actions or 'generateImages' in m.supported_actions:
         print(f" - {m.name} (Supported actions: {m.supported_actions})")
    elif 'image' in m.name.lower():
         print(f" - {m.name} (Actions: {m.supported_actions})")
