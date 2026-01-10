import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import json

# =====================================================
# ENV
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found in .env")

# =====================================================
# REQUEST
# =====================================================

URL = "https://openrouter.ai/api/v1/activity"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "HTTP-Referer": "http://localhost",
    "X-Title": "OpenRouter Activity Test Script",
}

params = {
    # "datestring": "2026-01-10"  # optional
}

print("Requesting OpenRouter activity...")

r = requests.get(URL, headers=HEADERS, params=params, timeout=30)

print("Status:", r.status_code)

if r.status_code != 200:
    print("Response:", r.text)
    r.raise_for_status()

data = r.json()

print("Keys:", data.keys())
print("Records:", len(data.get("data", [])))

# Pretty print first record
if data.get("data"):
    print("\nFirst record:\n")
    print(json.dumps(data["data"][0], indent=2))
