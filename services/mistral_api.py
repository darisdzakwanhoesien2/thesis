import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# -------------------------------------------------
# Always load env here (Streamlit safe)
# -------------------------------------------------
load_dotenv(Path(__file__).parent / ".env")

BASE = "https://api.mistral.ai/v1"


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def get_headers():
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY not found in environment")
    return {"Authorization": f"Bearer {key}"}


# -------------------------------------------------
# Upload
# -------------------------------------------------
def upload_file_for_ocr(file_path):
    url = f"{BASE}/files"

    with open(file_path, "rb") as f:
        r = requests.post(
            url,
            headers=get_headers(),
            files={"file": (Path(file_path).name, f)},
            data={"purpose": "ocr"},
            timeout=60,
        )

    if r.status_code != 200:
        raise RuntimeError(f"Upload failed: {r.text}")

    return r.json()["id"]


# -------------------------------------------------
# Signed URL
# -------------------------------------------------
def get_signed_url(file_id):
    url = f"{BASE}/files/{file_id}/url"

    r = requests.get(url, headers=get_headers(), timeout=30)

    if r.status_code != 200:
        raise RuntimeError(f"Signed URL failed: {r.text}")

    return r.json()["url"]


# -------------------------------------------------
# OCR
# -------------------------------------------------
def run_ocr_from_url(document_url):
    url = f"{BASE}/ocr"

    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": document_url,
        },
        "include_image_base64": True,
    }

    r = requests.post(
        url,
        headers={**get_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=180,
    )

    if r.status_code != 200:
        raise RuntimeError(f"OCR failed: {r.text}")

    return r.json()


# import os
# import requests

# MISTRAL_KEY = os.getenv("MISTRAL_API_KEY")

# BASE_URL = "https://api.mistral.ai/v1"

# HEADERS = {
#     "Authorization": f"Bearer {MISTRAL_KEY}"
# }


# # -------------------------
# # 1. AUTH TEST
# # -------------------------
# def test_auth():
#     url = f"{BASE_URL}/models"

#     r = requests.get(url, headers=HEADERS, timeout=20)

#     return r.status_code, r.text


# # -------------------------
# # 2. OCR CALL
# # -------------------------
# def run_ocr(file_path: str):

#     url = f"{BASE_URL}/ocr"

#     with open(file_path, "rb") as f:
#         files = {
#             "file": f
#         }

#         data = {
#             "model": "mistral-ocr-latest"
#         }

#         r = requests.post(
#             url,
#             headers=HEADERS,
#             files=files,
#             data=data,
#             timeout=120
#         )

#     if r.status_code != 200:
#         raise RuntimeError(f"OCR failed {r.status_code}: {r.text}")

#     result = r.json()

#     # ⚠️ adjust if API response changes
#     text = result.get("text", "")

#     return text, result


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