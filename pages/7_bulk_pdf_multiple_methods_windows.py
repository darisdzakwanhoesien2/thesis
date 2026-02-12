import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import json
import datetime
import time
import re
import os

from services.openrouter_client import call_openrouter

# =====================================================
# PATH SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

REGISTRY_PATH = LOGS_DIR / "registry.json"

DATA_DIR = BASE_DIR / "data"
MODELS_PATH = DATA_DIR / "models.json"

PROMPT_DIR = BASE_DIR / "prompts"
OUTPUTS_ROOT = BASE_DIR / "outputs_ocr/manual_batch" # "outputs"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📦 Bulk ABSA — Select OCR Outputs")
st.caption(f"Project root: {BASE_DIR}")

# =====================================================
# LOAD MODELS
# =====================================================

if not MODELS_PATH.exists():
    st.error("❌ data/models.json not found.")
    st.stop()

with open(MODELS_PATH, "r", encoding="utf-8") as f:
    models_cfg = json.load(f)

models = models_cfg.get("models", [])
if not models:
    st.error("❌ No models defined in models.json")
    st.stop()

label_to_id = {m["label"]: m["id"] for m in models}

# =====================================================
# LOAD PROMPTS
# =====================================================

st.sidebar.header("🧠 Prompt Methods")

if not PROMPT_DIR.exists():
    st.sidebar.error("❌ prompts/ directory not found.")
    st.stop()

prompt_files = sorted(PROMPT_DIR.glob("*.md"))
if not prompt_files:
    st.sidebar.error("❌ No .md prompt files found.")
    st.stop()

prompt_map = {p.name: p for p in prompt_files}

selected_prompt_names = st.sidebar.multiselect(
    "Select Prompt Methods",
    list(prompt_map.keys()),
    default=list(prompt_map.keys()),
)

if not selected_prompt_names:
    st.warning("Select at least one prompt.")
    st.stop()

preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")
st.text_area("📝 Preview Prompt", preview_prompt, height=200)

# =====================================================
# OCR FOLDER REFRESH + SELECTION
# =====================================================

st.sidebar.header("📂 OCR Outputs")

if not OUTPUTS_ROOT.exists():
    st.sidebar.error("❌ outputs/ directory not found.")
    st.stop()

# 🔄 Refresh Button
if st.sidebar.button("🔄 Refresh Folder List"):
    st.rerun()

# Force Windows filesystem refresh
os.scandir(OUTPUTS_ROOT)

# Detect folders recursively that contain pages/
pdf_folders = sorted(
    [
        p for p in OUTPUTS_ROOT.rglob("*")
        if p.is_dir() and (p / "pages").exists()
    ]
)

if not pdf_folders:
    st.sidebar.warning("No OCR folders detected.")
    st.stop()

# Multiselect after refresh
selected_pdfs = st.sidebar.multiselect(
    "Select OCR folders to process",
    pdf_folders,
    format_func=lambda p: p.name
)

if not selected_pdfs:
    st.warning("Select at least one OCR folder.")
    st.stop()

with st.expander("📁 Detected OCR Folders"):
    st.json([p.name for p in pdf_folders])

# =====================================================
# PAGE STRATEGY
# =====================================================

st.subheader("📄 Page Strategy")

page_mode = st.radio(
    "Choose page strategy:",
    ["ALL Pages per PDF", "Specific Page Range"]
)

if page_mode == "Specific Page Range":
    col1, col2 = st.columns(2)
    with col1:
        start_idx = st.number_input("Start Page Index", 0, 9999, 0)
    with col2:
        end_idx = st.number_input("End Page Index", 0, 9999, 3)

# =====================================================
# MODEL SETTINGS
# =====================================================

st.subheader("🤖 Model Settings")

selected_model_labels = st.multiselect(
    "Select Models",
    list(label_to_id.keys()),
    default=[list(label_to_id.keys())[0]]
)

if not selected_model_labels:
    st.warning("Select at least one model.")
    st.stop()

selected_models = [
    {
        "label": lbl,
        "id": label_to_id[lbl],
        "meta": next(m for m in models if m["label"] == lbl),
    }
    for lbl in selected_model_labels
]

temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
max_tokens = st.slider("Max Output Tokens", 512, 8192, 3000, 128)

# =====================================================
# EXPERIMENT SET
# =====================================================

st.subheader("🧪 Experiment Set")

default_set_name = f"MultiPDF_ABSA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
set_name = st.text_input("Experiment Set Name", default_set_name)

# =====================================================
# RUN
# =====================================================

if st.button("🚀 Run Bulk ABSA", type="primary"):

    saved_files = []

    total_jobs = (
        len(selected_pdfs)
        * len(selected_prompt_names)
        * len(selected_models)
    )

    job_idx = 0
    progress = st.progress(0)
    status = st.empty()

    for pdf_i, pdf in enumerate(selected_pdfs, start=1):

        pages_dir = pdf / "pages"
        page_files = sorted(pages_dir.glob("*.md"))

        if not page_files:
            st.warning(f"Skipping {pdf.name} — no pages found")
            continue

        if page_mode == "ALL Pages per PDF":
            selected_pages = page_files
        else:
            selected_pages = page_files[start_idx:end_idx + 1]

        combined_text = ""
        for p in selected_pages:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

        combined_text = combined_text[:24000]

        for prompt_name in selected_prompt_names:
            system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

            for model_cfg in selected_models:

                job_idx += 1
                model_id = model_cfg["id"]
                model_label = model_cfg["label"]

                status.info(
                    f"PDF {pdf_i}/{len(selected_pdfs)} | "
                    f"Job {job_idx}/{total_jobs}\n"
                    f"{pdf.name} | {prompt_name} | {model_label}"
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": combined_text},
                ]

                try:
                    output = call_openrouter(
                        messages=messages,
                        model=model_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

                    safe_pdf = re.sub(r'[^a-zA-Z0-9_-]', '_', pdf.name)
                    safe_prompt = re.sub(r'[^a-zA-Z0-9_-]', '_', prompt_name.replace('.md',''))
                    safe_model = re.sub(r'[^a-zA-Z0-9_-]', '_', model_label)

                    fname = f"absa_{ts}_{safe_pdf}_{safe_prompt}_{safe_model}.json"
                    log_path = LOGS_DIR / fname

                    log = {
                        "timestamp": ts,
                        "experiment_set": set_name,
                        "pdf": pdf.name,
                        "pages": [p.name for p in selected_pages],
                        "prompt_file": prompt_name,
                        "model": model_id,
                        "model_label": model_label,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "output": output,
                    }

                    with open(log_path, "w", encoding="utf-8") as f:
                        json.dump(log, f, indent=2)

                    saved_files.append(fname)

                except Exception as e:
                    st.error(f"{pdf.name} | {prompt_name} | {model_label} failed: {e}")

                progress.progress(job_idx / total_jobs)
                time.sleep(0.1)

    # Update registry (append safe)
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"sets": {}}

    registry.setdefault("sets", {})
    registry["sets"].setdefault(set_name, [])
    registry["sets"][set_name].extend(saved_files)

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    st.success("✅ Bulk ABSA Completed Successfully")
    st.json(saved_files)


# import streamlit as st
# from pathlib import Path
# from dotenv import load_dotenv
# import json
# import datetime
# import time
# import re
# import os

# from services.openrouter_client import call_openrouter

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# load_dotenv(BASE_DIR / ".env")

# LOGS_DIR = BASE_DIR / "logs"
# LOGS_DIR.mkdir(exist_ok=True)

# REGISTRY_PATH = LOGS_DIR / "registry.json"

# DATA_DIR = BASE_DIR / "data"
# MODELS_PATH = DATA_DIR / "models.json"

# PROMPT_DIR = BASE_DIR / "prompts"
# OUTPUTS_ROOT = BASE_DIR / "outputs"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("📦 Bulk ABSA — Auto OCR Processor")
# st.caption(f"Project root: {BASE_DIR}")

# # =====================================================
# # LOAD MODELS
# # =====================================================

# if not MODELS_PATH.exists():
#     st.error("❌ data/models.json not found.")
#     st.stop()

# with open(MODELS_PATH, "r", encoding="utf-8") as f:
#     models_cfg = json.load(f)

# models = models_cfg.get("models", [])
# if not models:
#     st.error("❌ No models defined in models.json")
#     st.stop()

# label_to_id = {m["label"]: m["id"] for m in models}

# # =====================================================
# # LOAD PROMPTS
# # =====================================================

# st.sidebar.header("🧠 Prompt Methods")

# if not PROMPT_DIR.exists():
#     st.sidebar.error("❌ prompts/ directory not found.")
#     st.stop()

# prompt_files = sorted(PROMPT_DIR.glob("*.md"))
# if not prompt_files:
#     st.sidebar.error("❌ No .md prompt files found.")
#     st.stop()

# prompt_map = {p.name: p for p in prompt_files}

# selected_prompt_names = st.sidebar.multiselect(
#     "Select Prompt Methods",
#     list(prompt_map.keys()),
#     default=list(prompt_map.keys()),
# )

# if not selected_prompt_names:
#     st.warning("Select at least one prompt.")
#     st.stop()

# preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")
# st.text_area("📝 Preview Prompt", preview_prompt, height=220)

# # =====================================================
# # AUTO DETECT OCR OUTPUTS
# # =====================================================

# st.sidebar.header("📂 OCR Outputs")

# if not OUTPUTS_ROOT.exists():
#     st.sidebar.error("❌ outputs/ directory not found.")
#     st.stop()

# if st.sidebar.button("🔄 Refresh Folder"):
#     st.rerun()

# # Force Windows filesystem refresh
# os.scandir(OUTPUTS_ROOT)

# pdf_folders = sorted(
#     [
#         p for p in OUTPUTS_ROOT.rglob("*")
#         if p.is_dir() and (p / "pages").exists()
#     ]
# )

# if not pdf_folders:
#     st.sidebar.error("❌ No OCR outputs detected (no pages/ folders).")
#     st.stop()

# st.sidebar.success(f"Detected {len(pdf_folders)} OCR folders")

# with st.expander("📁 Detected OCR Folders"):
#     st.json([p.name for p in pdf_folders])

# selected_pdfs = pdf_folders  # AUTO PROCESS ALL

# # =====================================================
# # PAGE MODE
# # =====================================================

# st.subheader("📄 Page Strategy")

# page_mode = st.radio(
#     "Choose page strategy:",
#     ["ALL Pages per PDF", "Specific Page Range"],
# )

# if page_mode == "Specific Page Range":
#     col1, col2 = st.columns(2)
#     with col1:
#         start_idx = st.number_input("Start Page Index", 0, 9999, 0)
#     with col2:
#         end_idx = st.number_input("End Page Index", 0, 9999, 3)

# # =====================================================
# # MODEL SETTINGS
# # =====================================================

# st.subheader("🤖 Model Settings")

# selected_model_labels = st.multiselect(
#     "Select Models",
#     list(label_to_id.keys()),
#     default=[list(label_to_id.keys())[0]],
# )

# if not selected_model_labels:
#     st.warning("Select at least one model.")
#     st.stop()

# selected_models = [
#     {
#         "label": lbl,
#         "id": label_to_id[lbl],
#         "meta": next(m for m in models if m["label"] == lbl),
#     }
#     for lbl in selected_model_labels
# ]

# temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
# max_tokens = st.slider("Max Output Tokens", 512, 8192, 3000, 128)

# # =====================================================
# # EXPERIMENT SET
# # =====================================================

# st.subheader("🧪 Experiment Set")

# default_set_name = f"MultiPDF_ABSA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
# set_name = st.text_input("Experiment Set Name", default_set_name)

# # =====================================================
# # RUN EXPERIMENT
# # =====================================================

# if st.button("🚀 Run Bulk ABSA", type="primary"):

#     saved_files = []

#     total_jobs = (
#         len(selected_pdfs)
#         * len(selected_prompt_names)
#         * len(selected_models)
#     )

#     job_idx = 0
#     progress = st.progress(0)
#     status = st.empty()

#     for pdf_i, pdf in enumerate(selected_pdfs, start=1):

#         pages_dir = pdf / "pages"
#         page_files = sorted(pages_dir.glob("*.md"))

#         if not page_files:
#             st.warning(f"Skipping {pdf.name} — no pages found")
#             continue

#         if page_mode == "ALL Pages per PDF":
#             selected_pages = page_files
#         else:
#             selected_pages = page_files[start_idx : end_idx + 1]

#         combined_text = ""
#         for p in selected_pages:
#             txt = p.read_text(encoding="utf-8", errors="ignore")
#             combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

#         combined_text = combined_text[:24000]  # safety limit

#         for prompt_name in selected_prompt_names:

#             system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

#             for model_cfg in selected_models:

#                 job_idx += 1

#                 model_id = model_cfg["id"]
#                 model_label = model_cfg["label"]

#                 status.info(
#                     f"PDF {pdf_i}/{len(selected_pdfs)} | "
#                     f"Job {job_idx}/{total_jobs}\n"
#                     f"{pdf.name} | {prompt_name} | {model_label}"
#                 )

#                 messages = [
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": combined_text},
#                 ]

#                 try:
#                     output = call_openrouter(
#                         messages=messages,
#                         model=model_id,
#                         temperature=temperature,
#                         max_tokens=max_tokens,
#                     )

#                     ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

#                     # Windows-safe filename
#                     safe_pdf = re.sub(r'[^a-zA-Z0-9_-]', '_', pdf.name)
#                     safe_prompt = re.sub(r'[^a-zA-Z0-9_-]', '_', prompt_name.replace('.md',''))
#                     safe_model = re.sub(r'[^a-zA-Z0-9_-]', '_', model_label)

#                     fname = f"absa_{ts}_{safe_pdf}_{safe_prompt}_{safe_model}.json"
#                     log_path = LOGS_DIR / fname

#                     log = {
#                         "timestamp": ts,
#                         "experiment_set": set_name,
#                         "pdf": pdf.name,
#                         "pages": [p.name for p in selected_pages],
#                         "prompt_file": prompt_name,
#                         "model": model_id,
#                         "model_label": model_label,
#                         "temperature": temperature,
#                         "max_tokens": max_tokens,
#                         "output": output,
#                     }

#                     with open(log_path, "w", encoding="utf-8") as f:
#                         json.dump(log, f, indent=2)

#                     saved_files.append(fname)

#                 except Exception as e:
#                     st.error(f"{pdf.name} | {prompt_name} | {model_label} failed: {e}")

#                 progress.progress(job_idx / total_jobs)
#                 time.sleep(0.1)

#     # =====================================================
#     # UPDATE REGISTRY (Append Safe)
#     # =====================================================

#     if REGISTRY_PATH.exists():
#         with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#             registry = json.load(f)
#     else:
#         registry = {"sets": {}}

#     registry.setdefault("sets", {})
#     registry["sets"].setdefault(set_name, [])
#     registry["sets"][set_name].extend(saved_files)

#     with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
#         json.dump(registry, f, indent=2)

#     st.success("✅ Bulk ABSA Completed Successfully")
#     st.write("Saved files:")
#     st.json(saved_files)
