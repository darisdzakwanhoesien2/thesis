import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("MISTRAL_API_KEY")
assert API_KEY, "❌ MISTRAL_API_KEY not found"

BASE = "https://api.mistral.ai/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TEST_FILE = Path("test.pdf")   # put any small pdf or image here


# -------------------------------------------------
# 1. Upload
# -------------------------------------------------
print("📤 Uploading file...")

with open(TEST_FILE, "rb") as f:
    r = requests.post(
        f"{BASE}/files",
        headers=HEADERS,
        files={"file": (TEST_FILE.name, f)},
        data={"purpose": "ocr"},
    )

print("Upload status:", r.status_code)
print(r.text)
r.raise_for_status()

file_id = r.json()["id"]
print("✅ File ID:", file_id)


# -------------------------------------------------
# 2. Get signed URL
# -------------------------------------------------
print("\n🔗 Getting signed URL...")

r = requests.get(f"{BASE}/files/{file_id}/url", headers=HEADERS)

print("URL status:", r.status_code)
print(r.text)
r.raise_for_status()

signed_url = r.json()["url"]
print("✅ Signed URL obtained")


# -------------------------------------------------
# 3. OCR
# -------------------------------------------------
print("\n🧠 Running OCR...")

payload = {
    "model": "mistral-ocr-latest",
    "document": {
        "type": "document_url",
        "document_url": signed_url
    }
}

r = requests.post(
    f"{BASE}/ocr",
    headers={**HEADERS, "Content-Type": "application/json"},
    json=payload,
)

print("OCR status:", r.status_code)
print(r.text[:1000])
r.raise_for_status()

print("✅ OCR success")
