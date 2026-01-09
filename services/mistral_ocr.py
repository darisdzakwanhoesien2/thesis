import os
import requests

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Example endpoint — adjust if Mistral updates OCR API
MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}"
}


def run_ocr(file_path: str):
    with open(file_path, "rb") as f:
        files = {
            "file": f
        }

        data = {
            "model": "mistral-ocr-latest"  # or vision-capable model
        }

        response = requests.post(
            MISTRAL_OCR_URL,
            headers=HEADERS,
            files=files,
            data=data,
            timeout=120
        )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    result = response.json()

    # Expected field may differ — adjust if needed
    text = result.get("text", "")

    return text, result