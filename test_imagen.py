import os
from google import genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("No GEMINI_API_KEY found")
    exit(1)

client = genai.Client(api_key=api_key)

print("Testing Image Generation with Imagen 4.0...")
try:
    response = client.models.generate_images(
        model='imagen-4.0-generate-001',
        prompt='A high-quality cinematic thumbnail for a viral video about technology bias, dramatic lighting, high contrast.',
    )
    
    # Save the first image
    if response.generated_images:
        img_data = response.generated_images[0].image.data
        with open("test_thumbnail.png", "wb") as f:
            f.write(img_data)
        print("Success! Image saved to test_thumbnail.png")
    else:
        print("No images generated.")

except Exception as e:
    print(f"Error generating image: {e}")
