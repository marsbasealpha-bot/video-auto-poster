import os
import logging
from google import genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

MODELS_TO_TRY = [
    'imagen-4.0-fast-generate-001',
    'gemini-2.0-flash-exp-image-generation',
    'gemini-3-pro-image-preview',
    'gemini-2.5-flash-image',
]

def try_models():
    prompt = "A high-quality cinematic thumbnail for a viral video about a Big Mac, dramatic lighting, high contrast."
    
    for model_name in MODELS_TO_TRY:
        print(f"\n--- Testing Model: {model_name} ---")
        try:
            response = client.models.generate_images(
                model=model_name,
                prompt=prompt,
            )
            if response.generated_images:
                print(f"SUCCESS with {model_name}!")
                with open(f"test_{model_name.replace('/','_')}.png", "wb") as f:
                    f.write(response.generated_images[0].image.data)
                return
            else:
                print(f"No images generated for {model_name}.")
        except Exception as e:
            print(f"Error for {model_name}: {e}")

if __name__ == "__main__":
    try_models()
