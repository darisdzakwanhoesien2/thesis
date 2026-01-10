import streamlit as st
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import shutil
import base64
import time

# =====================================================
# ENV
# =====================================================

BASE_DIR = Path(__file__).parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    st.error("❌ MISTRAL_API_KEY not found in .env")
    st.stop()

BASE = "https://api.mistral.ai/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TMP_DIR = BASE_DIR / "tmp_upload"
OUT_DIR = BASE_DIR / "outputs"

TMP_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

# =====================================================
# STREAMLIT CONFIG
# =====================================================

st.set_page_config(page_title="📚 Bulk OCR — Mistral", layout="wide")
st.title("📚 Bulk OCR Pipeline — Mistral OCR")

st.markdown("""
### Pipeline
1. Upload multiple PDFs / images  
2. Upload to Mistral  
3. Get signed URL  
4. Run OCR  
5. Save pages + images per document  
6. Download all as ZIP  
""")

# =====================================================
# FILE UPLOAD
# =====================================================

uploaded_files = st.file_uploader(
    "📤 Upload multiple thesis PDFs or scanned images",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

if uploaded_files:

    st.success(f"Uploaded {len(uploaded_files)} file(s)")

    if st.button("🚀 Run BULK OCR Pipeline"):

        # clean tmp
        if TMP_DIR.exists():
            shutil.rmtree(TMP_DIR)
        TMP_DIR.mkdir()

        # clean outputs
        if OUT_DIR.exists():
            shutil.rmtree(OUT_DIR)
        OUT_DIR.mkdir()

        progress = st.progress(0)
        status = st.empty()

        total = len(uploaded_files)

        for i, uploaded in enumerate(uploaded_files, start=1):

            status.info(f"Processing {i}/{total}: {uploaded.name}")

            # ---------------- Save temp file ----------------
            tmp_path = TMP_DIR / uploaded.name
            tmp_path.write_bytes(uploaded.getbuffer())

            doc_name = uploaded.name.replace(".", "_")
            out_root = OUT_DIR / doc_name
            pages_dir = out_root / "pages"
            images_dir = out_root / "images"
            pages_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)

            try:
                # ---------------- Upload ----------------
                with open(tmp_path, "rb") as f:
                    r = requests.post(
                        f"{BASE}/files",
                        headers=HEADERS,
                        files={"file": (tmp_path.name, f)},
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
                            img_name = img.get("id", f"img_{idx}.jpg")
                            (images_dir / img_name).write_bytes(img_bytes)

            except Exception as e:
                st.error(f"❌ Failed: {uploaded.name}")
                st.exception(e)

            progress.progress(i / total)
            time.sleep(0.2)

        status.success("✅ Bulk OCR completed!")

    # =================================================
    # OUTPUT DOWNLOAD
    # =================================================

    if OUT_DIR.exists() and any(OUT_DIR.iterdir()):

        zip_path = BASE_DIR / "bulk_ocr_outputs.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in OUT_DIR.rglob("*"):
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

        docs = sorted([p for p in OUT_DIR.iterdir() if p.is_dir()])

        if docs:
            doc = st.selectbox("Select document", docs, format_func=lambda p: p.name)

            pages = sorted((doc / "pages").glob("*.md"))
            images = sorted((doc / "images").glob("*"))

            if pages:
                page = st.selectbox(
                    "Select page",
                    pages,
                    format_func=lambda p: p.name,
                )

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
        else:
            st.info("No OCR results yet.")
