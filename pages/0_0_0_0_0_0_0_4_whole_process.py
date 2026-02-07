import streamlit as st
import requests
import json
import base64
import time
from pathlib import Path
from datetime import datetime
import os
from dotenv import load_dotenv

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(page_title="Bulk Link PDF + OCR Pipeline", layout="wide")
st.title("📥➡️📚 Bulk Link PDF Download + OCR (Batch Safe)")

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("MISTRAL_API_KEY")
BASE = "https://api.mistral.ai/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PDF_DIR = BASE_DIR / "data" / "sustainability_pdfs"
OCR_DIR = BASE_DIR / "outputs_ocr"
DATA_JSON = BASE_DIR / "data" / "download_ocr.json"

PDF_DIR.mkdir(parents=True, exist_ok=True)
OCR_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# UTILITIES
# =====================================================

def safe_filename(name):
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)

def timestamp():
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def load_tracking():
    if DATA_JSON.exists():
        return json.loads(DATA_JSON.read_text())
    return []

def save_tracking(data):
    DATA_JSON.write_text(json.dumps(data, indent=2))

def download_pdf(url, out_path):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    out_path.write_bytes(r.content)

def run_ocr(pdf_path, company):

    doc_ts = timestamp()
    doc_name = pdf_path.stem
    out_root = OCR_DIR / company / f"{doc_name}_{doc_ts}"
    pages_dir = out_root / "pages"
    images_dir = out_root / "images"

    pages_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    # Upload
    with open(pdf_path, "rb") as f:
        r = requests.post(
            f"{BASE}/files",
            headers=HEADERS,
            files={"file": (pdf_path.name, f)},
            data={"purpose": "ocr"},
            timeout=120,
        )
    r.raise_for_status()
    file_id = r.json()["id"]

    # Signed URL
    r = requests.get(f"{BASE}/files/{file_id}/url", headers=HEADERS)
    r.raise_for_status()
    signed_url = r.json()["url"]

    # OCR
    payload = {
        "model": "mistral-ocr-latest",
        "document": {
            "type": "document_url",
            "document_url": signed_url,
        },
        "include_image_base64": True,
    }

    r = requests.post(
        f"{BASE}/ocr",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    r.raise_for_status()

    result = r.json()
    pages = result.get("pages", [])

    for p in pages:
        idx = p.get("index", 0)
        md = p.get("markdown", "")
        (pages_dir / f"page_{idx:04d}.md").write_text(md, encoding="utf-8")

        for img in p.get("images", []):
            if img.get("image_base64"):
                img_bytes = base64.b64decode(img["image_base64"])
                img_name = safe_filename(img.get("id", f"img_{idx}.jpg"))
                (images_dir / img_name).write_bytes(img_bytes)

    return out_root

# =====================================================
# UI
# =====================================================

st.subheader("🔗 Paste Multiple PDF Links (one per line)")

link_input = st.text_area(
    "Enter URLs:",
    height=250,
    placeholder="https://example.com/report1.pdf\nhttps://example.com/report2.pdf"
)

company_name = st.text_input("🏢 Company Name", value="manual_batch")

if st.button("🚀 Run Download + OCR Batch"):

    if not link_input.strip():
        st.error("Please enter at least one URL.")
        st.stop()

    links = [l.strip() for l in link_input.splitlines() if l.strip()]
    tracking = load_tracking()

    progress = st.progress(0)
    status_box = st.empty()

    total = len(links)

    for i, url in enumerate(links, start=1):

        status_box.info(f"Processing {i}/{total}: {url}")

        file_ts = timestamp()
        file_name = safe_filename(Path(url).stem) or f"file_{i}"
        pdf_filename = f"{file_name}_{file_ts}.pdf"
        pdf_path = PDF_DIR / company_name
        pdf_path.mkdir(exist_ok=True)

        final_pdf_path = pdf_path / pdf_filename

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "url": url,
            "company": company_name,
            "pdf_filename": str(final_pdf_path),
            "status": None,
            "ocr_output": None,
            "error": None
        }

        try:
            # ---------------- Download ----------------
            download_pdf(url, final_pdf_path)
            record["status"] = "downloaded"

            # ---------------- OCR ----------------
            ocr_out = run_ocr(final_pdf_path, company_name)
            record["ocr_output"] = str(ocr_out)
            record["status"] = "completed"

            st.success(f"✅ Done: {pdf_filename}")

        except Exception as e:
            record["status"] = "failed"
            record["error"] = str(e)
            st.error(f"❌ Failed: {url}")

        # Save after EACH document
        tracking.append(record)
        save_tracking(tracking)

        progress.progress(i / total)
        time.sleep(0.2)

    status_box.success("🎉 Batch Finished Safely!")

# =====================================================
# TRACKING TABLE
# =====================================================

st.divider()
st.subheader("📊 Download + OCR Tracking")

tracking_data = load_tracking()

if tracking_data:
    st.dataframe(tracking_data, use_container_width=True)
else:
    st.info("No records yet.")
