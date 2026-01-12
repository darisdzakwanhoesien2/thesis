import streamlit as st
import json
from pathlib import Path
import requests

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="📥 Sustainability PDF Downloader", layout="wide")
st.title("📥 Download Sustainability PDFs from JSON")

st.markdown("""
This page loads sustainability report metadata from JSON files and downloads
the linked PDFs into local storage.

**Source folder:** `data/sustainability_json/`  
**Output folder:** `data/sustainability_pdfs/<json_name>/`
""")

# =====================================================
# PATHS
# =====================================================
BASE_DIR = Path(__file__).resolve().parents[1]

JSON_DIR = BASE_DIR / "data" / "sustainability_json"
PDF_DIR = BASE_DIR / "data" / "sustainability_pdfs"

JSON_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# UTIL
# =====================================================
def safe_filename(name: str):
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip()


def download_pdf(url, out_path):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)


# =====================================================
# LOAD JSON FILE LIST
# =====================================================
json_files = sorted(JSON_DIR.glob("*.json"))

if not json_files:
    st.warning("No JSON files found in data/sustainability_json/")
    st.stop()

json_map = {f.name: f for f in json_files}

selected_json_name = st.selectbox(
    "📂 Select JSON dataset",
    list(json_map.keys())
)

json_path = json_map[selected_json_name]

# =====================================================
# LOAD JSON CONTENT
# =====================================================
try:
    with open(json_path, "r", encoding="utf-8") as f:
        records = json.load(f)
except Exception as e:
    st.error(f"Failed to load JSON: {e}")
    st.stop()

if not isinstance(records, list):
    st.error("JSON must be a list of report objects.")
    st.stop()

st.success(f"Loaded {len(records)} records from {selected_json_name}")

# =====================================================
# OUTPUT DIRECTORY PER JSON
# =====================================================
dataset_name = json_path.stem
OUT_DIR = PDF_DIR / dataset_name
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# TABLE VIEW
# =====================================================
st.subheader("📄 Available Reports")

for i, rec in enumerate(records, start=1):
    with st.container(border=True):
        cols = st.columns([4, 2, 2, 2])

        title = rec.get("title", "Unknown")
        date = rec.get("date", "-")
        rtype = rec.get("type", "-")
        url = rec.get("pdf_link")

        fname = safe_filename(title) + ".pdf"
        out_path = OUT_DIR / fname

        cols[0].markdown(f"**{i}. {title}**")
        cols[1].markdown(f"📅 {date}")
        cols[2].markdown(f"📘 {rtype}")

        if out_path.exists():
            cols[3].success("Downloaded")
        else:
            if cols[3].button("⬇️ Download", key=f"dl_{i}"):
                try:
                    download_pdf(url, out_path)
                    st.success(f"Saved: {out_path.name}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        with st.expander("🔗 PDF link"):
            st.write(url)

# =====================================================
# BULK DOWNLOAD
# =====================================================
st.divider()
st.subheader("📦 Bulk Download")

missing = []
for rec in records:
    fname = safe_filename(rec.get("title", "report")) + ".pdf"
    if not (OUT_DIR / fname).exists():
        missing.append(rec)

col1, col2 = st.columns(2)

col1.markdown(f"""
**Target folder:**  
`{OUT_DIR.relative_to(BASE_DIR)}`
""")

if not missing:
    col2.success("All PDFs already downloaded ✅")
else:
    if col2.button(f"⬇️ Download All Missing ({len(missing)})"):
        progress = st.progress(0)
        errors = []

        for i, rec in enumerate(missing, start=1):
            try:
                fname = safe_filename(rec.get("title", "report")) + ".pdf"
                out_path = OUT_DIR / fname
                download_pdf(rec["pdf_link"], out_path)
            except Exception as e:
                errors.append((rec.get("title"), str(e)))

            progress.progress(i / len(missing))

        if errors:
            st.error("Some downloads failed:")
            for t, e in errors:
                st.write(f"- {t}: {e}")
        else:
            st.success("All PDFs downloaded successfully ✅")

        st.rerun()

# =====================================================
# FILE BROWSER
# =====================================================
st.divider()
st.subheader("📁 Downloaded Files")

pdf_files = sorted(OUT_DIR.glob("*.pdf"))

if not pdf_files:
    st.info("No PDFs downloaded yet.")
else:
    for p in pdf_files:
        st.write(f"- {p.name}")
