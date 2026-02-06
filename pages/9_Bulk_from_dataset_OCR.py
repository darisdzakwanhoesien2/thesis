import streamlit as st
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import base64
import time
import json

# =====================================================
# PATH & ENV
# =====================================================

BASE_DIR = Path(__file__).parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    st.error("❌ MISTRAL_API_KEY not found in .env")
    st.stop()

BASE = "https://api.mistral.ai/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PDF_ROOT = BASE_DIR / "data" / "sustainability_pdfs"
OUT_DIR = BASE_DIR / "outputs_ocr"
LOG_DIR = BASE_DIR / "logs"

OUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "bulk_ocr_log.json"

# =====================================================
# STREAMLIT CONFIG
# =====================================================

st.set_page_config(page_title="📚 Bulk OCR — Sustainability PDFs", layout="wide")
st.title("📚 Bulk OCR from Sustainability PDF Folders (Mistral OCR)")

st.markdown("""
### Pipeline
1. Select company folders  
2. Select PDFs  
3. Upload to Mistral via signed URL  
4. Run OCR  
5. Save pages + images per document  
6. Resume-safe (skip processed)  
7. Download all OCR outputs as ZIP  
""")

# =====================================================
# UTIL
# =====================================================

def safe_name(name: str):
    return name.replace("/", "_").replace("\\", "_")

def load_log():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {}

def save_log(log):
    LOG_FILE.write_text(json.dumps(log, indent=2))


# =====================================================
# COMPANY & PDF SELECTION
# =====================================================

if not PDF_ROOT.exists():
    st.error(f"❌ Folder not found: {PDF_ROOT}")
    st.stop()

companies = sorted([p for p in PDF_ROOT.iterdir() if p.is_dir()])

selected_companies = st.multiselect(
    "🏢 Select companies",
    companies,
    format_func=lambda p: p.name,
)

selected_pdfs = []

for comp in selected_companies:
    pdfs = sorted(comp.glob("*.pdf"))
    if pdfs:
        chosen = st.multiselect(
            f"📄 Select PDFs for {comp.name}",
            pdfs,
            default=pdfs,
            format_func=lambda p: p.name,
        )
        selected_pdfs.extend(chosen)

st.info(f"Total selected PDFs: {len(selected_pdfs)}")

# =====================================================
# RUN OCR
# =====================================================

if "ocr_done" not in st.session_state:
    st.session_state["ocr_done"] = False

if selected_pdfs and st.button("🚀 Run BULK OCR Pipeline"):

    st.session_state["ocr_done"] = False

    log = load_log()

    progress = st.progress(0)
    status = st.empty()

    total = len(selected_pdfs)

    for i, pdf_path in enumerate(selected_pdfs, start=1):

        company = pdf_path.parent.name
        doc_key = f"{company}/{pdf_path.name}"

        status.info(f"Processing {i}/{total}: {doc_key}")

        if doc_key in log and log[doc_key]["status"] == "done":
            status.warning(f"⏭ Skipped (already processed): {doc_key}")
            progress.progress(i / total)
            continue

        doc_name = pdf_path.stem
        out_root = OUT_DIR / company / doc_name
        pages_dir = out_root / "pages"
        images_dir = out_root / "images"
        pages_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            # ---------------- Upload ----------------
            with open(pdf_path, "rb") as f:
                r = requests.post(
                    f"{BASE}/files",
                    headers=HEADERS,
                    files={"file": (pdf_path.name, f)},
                    data={"purpose": "ocr"},
                    timeout=120,
                )
            if r.status_code != 200:
                raise RuntimeError(f"Upload failed: {r.text}")
            file_id = r.json()["id"]

            # ---------------- Signed URL ----------------
            r = requests.get(
                f"{BASE}/files/{file_id}/url",
                headers=HEADERS,
                timeout=60,
            )
            if r.status_code != 200:
                raise RuntimeError(f"Signed URL failed: {r.text}")
            signed_url = r.json()["url"]

            # ---------------- OCR ----------------
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
            if r.status_code != 200:
                raise RuntimeError(f"OCR failed: {r.text}")

            result = r.json()

            # ---------------- Save Pages ----------------
            pages = result.get("pages", [])
            for p in pages:
                idx = p.get("index", 0)
                md = p.get("markdown", "")

                (pages_dir / f"page_{idx:04d}.md").write_text(md, encoding="utf-8")

                for img in p.get("images", []):
                    if img.get("image_base64"):
                        img_bytes = base64.b64decode(img["image_base64"])
                        raw_name = img.get("id", f"img_{idx}.jpg")
                        img_name = Path(raw_name).name
                        (images_dir / img_name).write_bytes(img_bytes)

            log[doc_key] = {
                "status": "done",
                "company": company,
                "pages": len(pages),
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_log(log)

        except Exception as e:
            log[doc_key] = {"status": "failed", "error": str(e)}
            save_log(log)
            st.error(f"❌ Failed: {doc_key}")
            st.exception(e)

        progress.progress(i / total)
        time.sleep(0.2)

    status.success("✅ Bulk OCR completed!")
    st.session_state["ocr_done"] = True


# =================================================
# OUTPUT DOWNLOAD
# =================================================

if OUT_DIR.exists() and any(OUT_DIR.rglob("pages")):

    zip_path = BASE_DIR / "bulk_ocr_outputs.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in OUT_DIR.rglob("*"):
            if p.is_file():
                z.write(p, arcname=p.relative_to(OUT_DIR))

    with open(zip_path, "rb") as f:
        st.download_button(
            "⬇ Download ALL OCR Results (ZIP)",
            data=f,
            file_name="bulk_ocr_outputs.zip",
            mime="application/zip",
        )

    st.divider()

    # =================================================
    # PREVIEW
    # =================================================

    st.subheader("🔍 Preview OCR Output")

    companies_out = sorted([p for p in OUT_DIR.iterdir() if p.is_dir()])

    company_sel = st.selectbox("Company", companies_out, format_func=lambda p: p.name)

    docs = sorted([p for p in company_sel.iterdir() if p.is_dir()])

    doc = st.selectbox("Document", docs, format_func=lambda p: p.name)

    pages = sorted((doc / "pages").glob("*.md"))
    images = sorted((doc / "images").glob("*"))

    if pages:
        page = st.selectbox("Page", pages, format_func=lambda p: p.name)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### OCR Text")
            st.text_area(
                "",
                value=page.read_text(encoding="utf-8", errors="ignore"),
                height=500,
            )

        with col2:
            st.markdown("### Images")
            for img in images:
                st.image(str(img), use_container_width=True)
