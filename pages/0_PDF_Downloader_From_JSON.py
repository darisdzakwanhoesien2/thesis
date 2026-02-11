import streamlit as st
import json
from pathlib import Path
import requests
from datetime import datetime

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(page_title="📥 Sustainability PDF Downloader", layout="wide")
st.title("📥 Sustainability PDF Downloader (Flexible JSON + Logging)")

st.markdown("""
Download sustainability PDFs from JSON metadata with:

- ✅ selectable URL field  
- ✅ optional base URL  
- ✅ run tag for experiments  
- ✅ structured logs  

**JSON folder:** `data/sustainability_json/`  
**PDF output:** `data/sustainability_pdfs/<json_name>/`  
**Logs:** `logs/pdf_download_log.jsonl`
""")

# =====================================================
# PATHS
# =====================================================
BASE_DIR = Path(__file__).resolve().parents[1]

JSON_DIR = BASE_DIR / "data" / "sustainability_json"
PDF_DIR = BASE_DIR / "data" / "sustainability_pdfs"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "pdf_download_log.jsonl"

JSON_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# UTIL
# =====================================================
def safe_filename(name: str):
    return "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip()


def normalize_url(base_url: str, path: str):
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not base_url:
        return None
    return base_url.rstrip("/") + "/" + path.lstrip("/")


def download_pdf(url, out_path):
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(r.content)


def write_log(entry: dict):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

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

if not isinstance(records, list) or not records:
    st.error("JSON must be a non-empty list of objects.")
    st.stop()

st.success(f"Loaded {len(records)} records from {selected_json_name}")

# =====================================================
# COLUMN DETECTION
# =====================================================
all_keys = sorted({k for r in records for k in r.keys()})

st.subheader("🔧 URL & Tag Configuration")

colA, colB, colC = st.columns(3)

with colA:
    url_field = st.selectbox(
        "🔗 Select field containing PDF URL / path",
        all_keys,
        index=all_keys.index("pdf_link") if "pdf_link" in all_keys else 0,
    )

with colB:
    base_url = st.text_input(
        "🌐 Optional Base URL (for relative paths)",
        placeholder="https://www.company.com/reports"
    )

with colC:
    run_tag = st.text_input(
        "🏷️ Run Tag (saved to logs)",
        value=f"{json_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

# =====================================================
# OUTPUT DIRECTORY PER JSON
# =====================================================
dataset_name = json_path.stem
OUT_DIR = PDF_DIR / dataset_name
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# TABLE VIEW
# =====================================================
st.divider()
st.subheader("📄 Available Reports")

for i, rec in enumerate(records, start=1):
    with st.container(border=True):
        cols = st.columns([4, 2, 2, 2])

        title = rec.get("title", f"report_{i}")
        date = rec.get("date", "-")
        rtype = rec.get("type", "-")
        raw_path = rec.get(url_field)

        final_url = normalize_url(base_url, raw_path)

        fname = safe_filename(title) + ".pdf"
        out_path = OUT_DIR / fname

        cols[0].markdown(f"**{i}. {title}**")
        cols[1].markdown(f"📅 {date}")
        cols[2].markdown(f"📘 {rtype}")

        if out_path.exists():
            cols[3].success("Downloaded")
        else:
            if cols[3].button("⬇️ Download", key=f"dl_{i}"):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "json_file": selected_json_name,
                    "url_field": url_field,
                    "base_url": base_url,
                    "tag": run_tag,
                    "title": title,
                    "raw_value": raw_path,
                    "final_url": final_url,
                }

                try:
                    if not final_url:
                        raise ValueError("Final URL is empty (check base URL and field)")

                    download_pdf(final_url, out_path)
                    log_entry["status"] = "success"
                    st.success(f"Saved: {out_path.name}")
                    write_log(log_entry)
                    st.rerun()

                except Exception as e:
                    log_entry["status"] = "error"
                    log_entry["error"] = str(e)
                    write_log(log_entry)
                    st.error(str(e))

        with st.expander("🔗 URL details"):
            st.write("Raw value:", raw_path)
            st.write("Final URL:", final_url)

# =====================================================
# BULK DOWNLOAD
# =====================================================
st.divider()
st.subheader("📦 Bulk Download")

missing = []
for rec in records:
    title = rec.get("title", "report")
    fname = safe_filename(title) + ".pdf"
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
            title = rec.get("title", f"report_{i}")
            raw_path = rec.get(url_field)
            final_url = normalize_url(base_url, raw_path)
            fname = safe_filename(title) + ".pdf"
            out_path = OUT_DIR / fname

            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "json_file": selected_json_name,
                "url_field": url_field,
                "base_url": base_url,
                "tag": run_tag,
                "title": title,
                "raw_value": raw_path,
                "final_url": final_url,
            }

            try:
                if not final_url:
                    raise ValueError("Final URL is empty")

                download_pdf(final_url, out_path)
                log_entry["status"] = "success"

            except Exception as e:
                log_entry["status"] = "error"
                log_entry["error"] = str(e)
                errors.append((title, str(e)))

            write_log(log_entry)
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

# =====================================================
# LOG INFO
# =====================================================
st.divider()
st.subheader("📝 Logging")

st.write(f"Logs saved to: `{LOG_FILE.relative_to(BASE_DIR)}`")

if LOG_FILE.exists():
    st.caption(f"Total log lines: {sum(1 for _ in open(LOG_FILE, 'r', encoding='utf-8'))}")


# import streamlit as st
# import json
# from pathlib import Path
# import requests

# # =====================================================
# # PAGE CONFIG
# # =====================================================
# st.set_page_config(page_title="📥 Sustainability PDF Downloader", layout="wide")
# st.title("📥 Download Sustainability PDFs from JSON")

# st.markdown("""
# This page loads sustainability report metadata from JSON files and downloads
# the linked PDFs into local storage.

# **Source folder:** `data/sustainability_json/`  
# **Output folder:** `data/sustainability_pdfs/<json_name>/`
# """)

# # =====================================================
# # PATHS
# # =====================================================
# BASE_DIR = Path(__file__).resolve().parents[1]

# JSON_DIR = BASE_DIR / "data" / "sustainability_json"
# PDF_DIR = BASE_DIR / "data" / "sustainability_pdfs"

# JSON_DIR.mkdir(parents=True, exist_ok=True)
# PDF_DIR.mkdir(parents=True, exist_ok=True)

# # =====================================================
# # UTIL
# # =====================================================
# def safe_filename(name: str):
#     return "".join(c if c.isalnum() or c in "._- " else "_" for c in name).strip()


# def download_pdf(url, out_path):
#     r = requests.get(url, timeout=60)
#     r.raise_for_status()
#     with open(out_path, "wb") as f:
#         f.write(r.content)


# # =====================================================
# # LOAD JSON FILE LIST
# # =====================================================
# json_files = sorted(JSON_DIR.glob("*.json"))

# if not json_files:
#     st.warning("No JSON files found in data/sustainability_json/")
#     st.stop()

# json_map = {f.name: f for f in json_files}

# selected_json_name = st.selectbox(
#     "📂 Select JSON dataset",
#     list(json_map.keys())
# )

# json_path = json_map[selected_json_name]

# # =====================================================
# # LOAD JSON CONTENT
# # =====================================================
# try:
#     with open(json_path, "r", encoding="utf-8") as f:
#         records = json.load(f)
# except Exception as e:
#     st.error(f"Failed to load JSON: {e}")
#     st.stop()

# if not isinstance(records, list):
#     st.error("JSON must be a list of report objects.")
#     st.stop()

# st.success(f"Loaded {len(records)} records from {selected_json_name}")

# # =====================================================
# # OUTPUT DIRECTORY PER JSON
# # =====================================================
# dataset_name = json_path.stem
# OUT_DIR = PDF_DIR / dataset_name
# OUT_DIR.mkdir(parents=True, exist_ok=True)

# # =====================================================
# # TABLE VIEW
# # =====================================================
# st.subheader("📄 Available Reports")

# for i, rec in enumerate(records, start=1):
#     with st.container(border=True):
#         cols = st.columns([4, 2, 2, 2])

#         title = rec.get("title", "Unknown")
#         date = rec.get("date", "-")
#         rtype = rec.get("type", "-")
#         url = rec.get("pdf_link")

#         fname = safe_filename(title) + ".pdf"
#         out_path = OUT_DIR / fname

#         cols[0].markdown(f"**{i}. {title}**")
#         cols[1].markdown(f"📅 {date}")
#         cols[2].markdown(f"📘 {rtype}")

#         if out_path.exists():
#             cols[3].success("Downloaded")
#         else:
#             if cols[3].button("⬇️ Download", key=f"dl_{i}"):
#                 try:
#                     download_pdf(url, out_path)
#                     st.success(f"Saved: {out_path.name}")
#                     st.rerun()
#                 except Exception as e:
#                     st.error(str(e))

#         with st.expander("🔗 PDF link"):
#             st.write(url)

# # =====================================================
# # BULK DOWNLOAD
# # =====================================================
# st.divider()
# st.subheader("📦 Bulk Download")

# missing = []
# for rec in records:
#     fname = safe_filename(rec.get("title", "report")) + ".pdf"
#     if not (OUT_DIR / fname).exists():
#         missing.append(rec)

# col1, col2 = st.columns(2)

# col1.markdown(f"""
# **Target folder:**  
# `{OUT_DIR.relative_to(BASE_DIR)}`
# """)

# if not missing:
#     col2.success("All PDFs already downloaded ✅")
# else:
#     if col2.button(f"⬇️ Download All Missing ({len(missing)})"):
#         progress = st.progress(0)
#         errors = []

#         for i, rec in enumerate(missing, start=1):
#             try:
#                 fname = safe_filename(rec.get("title", "report")) + ".pdf"
#                 out_path = OUT_DIR / fname
#                 download_pdf(rec["pdf_link"], out_path)
#             except Exception as e:
#                 errors.append((rec.get("title"), str(e)))

#             progress.progress(i / len(missing))

#         if errors:
#             st.error("Some downloads failed:")
#             for t, e in errors:
#                 st.write(f"- {t}: {e}")
#         else:
#             st.success("All PDFs downloaded successfully ✅")

#         st.rerun()

# # =====================================================
# # FILE BROWSER
# # =====================================================
# st.divider()
# st.subheader("📁 Downloaded Files")

# pdf_files = sorted(OUT_DIR.glob("*.pdf"))

# if not pdf_files:
#     st.info("No PDFs downloaded yet.")
# else:
#     for p in pdf_files:
#         st.write(f"- {p.name}")
