import os
import google.generativeai as genai
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

model_name = 'gemini-2.0-flash-exp-image-generation'
print(f"Testing with google-generativeai SDK and model: {model_name}")

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Generate a cinematic thumbnail of a juicy Big Mac on a dramatic dark background.")
    
    # Check if there are any parts that are images
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            print("SUCCESS: Found inline image data!")
            with open("test_generativeai_sdk.png", "wb") as f:
                f.write(part.inline_data.data)
            break
    else:
        print("No image data found in response parts.")
        print(f"Response text: {response.text}")
except Exception as e:
    print(f"Error: {e}")
