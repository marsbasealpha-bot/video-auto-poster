import os
import requests
import json
import base64
import dotenv

dotenv.load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Try the v1alpha endpoint for the experimental model
url = f"https://generativelanguage.googleapis.com/v1alpha/models/gemini-2.0-flash-exp-image-generation:predict?key={api_key}"

payload = {
    "instances": [
        {"prompt": "A high-quality cinematic thumbnail for a viral video about a Big Mac, dramatic lighting, high contrast."}
    ],
    "parameters": {
        "sampleCount": 1
    }
}

print(f"Testing raw HTTP for v1alpha and model: gemini-2.0-flash-exp-image-generation")
try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        if 'predictions' in res_json:
            img_b64 = res_json['predictions'][0]['bytesBase64Encoded']
            with open("test_raw_http.png", "wb") as f:
                f.write(base64.b64decode(img_b64))
            print("SUCCESS: Image generated and saved!")
        else:
            print("No predictions found in response.")
            print(json.dumps(res_json, indent=2))
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
