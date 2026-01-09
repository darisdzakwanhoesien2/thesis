import os
import requests

BASE = "https://api.mistral.ai/v1"
KEY = os.getenv("MISTRAL_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {KEY}"
}


def upload_file_for_ocr(file_path):
    url = f"{BASE}/files"

    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"purpose": "ocr"}

        r = requests.post(url, headers=HEADERS, files=files, data=data, timeout=60)

    if r.status_code != 200:
        raise RuntimeError(f"Upload failed: {r.text}")

    return r.json()["id"]


def get_signed_url(file_id):
    url = f"{BASE}/files/{file_id}/url"
    params = {"expiry": 24}

    r = requests.get(url, headers=HEADERS, params=params, timeout=30)

    if r.status_code != 200:
        raise RuntimeError(f"Signed URL failed: {r.text}")

    return r.json()["url"]


def run_ocr_from_url(document_url):
    url = f"{BASE}/ocr"

    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": document_url
        },
        "include_image_base64": True
    }

    r = requests.post(url, headers=HEADERS, json=payload, timeout=180)

    if r.status_code != 200:
        raise RuntimeError(f"OCR failed: {r.text}")

    return r.json()
