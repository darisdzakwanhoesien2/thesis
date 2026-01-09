import os
import requests

MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")

BASE_URL = "https://api.mistral.ai/v1"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_KEY}"
}


# -------------------------
# 1. AUTH TEST
# -------------------------
def test_auth():
    url = f"{BASE_URL}/models"

    r = requests.get(url, headers=HEADERS, timeout=20)

    return r.status_code, r.text


# -------------------------
# 2. OCR CALL
# -------------------------
def run_ocr(file_path: str):

    url = f"{BASE_URL}/ocr"

    with open(file_path, "rb") as f:
        files = {
            "file": f
        }

        data = {
            "model": "mistral-ocr-latest"
        }

        r = requests.post(
            url,
            headers=HEADERS,
            files=files,
            data=data,
            timeout=120
        )

    if r.status_code != 200:
        raise RuntimeError(f"OCR failed {r.status_code}: {r.text}")

    result = r.json()

    # ⚠️ adjust if API response changes
    text = result.get("text", "")

    return text, result


# import os
# import requests

# MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# # Example endpoint — adjust if Mistral updates OCR API
# MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"

# HEADERS = {
#     "Authorization": f"Bearer {MISTRAL_API_KEY}"
# }


# def run_ocr(file_path: str):
#     with open(file_path, "rb") as f:
#         files = {
#             "file": f
#         }

#         data = {
#             "model": "mistral-ocr-latest"  # or vision-capable model
#         }

#         response = requests.post(
#             MISTRAL_OCR_URL,
#             headers=HEADERS,
#             files=files,
#             data=data,
#             timeout=120
#         )

#     if response.status_code != 200:
#         raise RuntimeError(response.text)

#     result = response.json()

#     # Expected field may differ — adjust if needed
#     text = result.get("text", "")

#     return text, result