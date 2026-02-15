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
OUTPUTS_ROOT = BASE_DIR / "outputs_ocr/manual_batch"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📦 Bulk ABSA — Smart Resume Engine")
st.caption(f"Project root: {BASE_DIR}")

# =====================================================
# UTIL FUNCTIONS
# =====================================================

def safe_name(text):
    return re.sub(r'[^a-zA-Z0-9_-]', '_', text)

def get_processed_jobs():
    """
    Returns set of (pdf, prompt, model_label)
    """
    processed = set()
    log_files = list(LOGS_DIR.glob("absa_*.json"))

    for file in log_files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                log = json.load(f)
                key = (
                    log.get("pdf"),
                    log.get("prompt_file"),
                    log.get("model_label")
                )
                processed.add(key)
        except:
            continue

    return processed

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
    st.error("❌ No models defined.")
    st.stop()

label_to_id = {m["label"]: m["id"] for m in models}

# =====================================================
# LOAD PROMPTS
# =====================================================

st.sidebar.header("🧠 Prompt Methods")

prompt_files = sorted(PROMPT_DIR.glob("*.md"))
if not prompt_files:
    st.sidebar.error("No prompts found.")
    st.stop()

prompt_map = {p.name: p for p in prompt_files}

selected_prompt_names = st.sidebar.multiselect(
    "Select Prompt Methods",
    list(prompt_map.keys()),
    default=list(prompt_map.keys()),
)

if not selected_prompt_names:
    st.stop()

# =====================================================
# LOAD OCR FOLDERS
# =====================================================

st.sidebar.header("📂 OCR Outputs")

if not OUTPUTS_ROOT.exists():
    st.sidebar.error("OCR root not found.")
    st.stop()

pdf_folders = sorted(
    [
        p for p in OUTPUTS_ROOT.rglob("*")
        if p.is_dir() and (p / "pages").exists()
    ]
)

if not pdf_folders:
    st.sidebar.warning("No OCR folders detected.")
    st.stop()

processed_jobs = get_processed_jobs()

# =====================================================
# PROCESS MODE
# =====================================================

st.sidebar.markdown("### ⚙️ Processing Mode")

process_mode = st.sidebar.radio(
    "Choose mode:",
    ["Process Only Remaining", "Process All (Force Re-run)"]
)

def is_remaining(pdf_name):
    for prompt_name in selected_prompt_names:
        for model_label in label_to_id.keys():
            if (pdf_name, prompt_name, model_label) not in processed_jobs:
                return True
    return False

remaining_folders = [p for p in pdf_folders if is_remaining(p.name)]

if process_mode == "Process Only Remaining":
    default_selection = remaining_folders
else:
    default_selection = pdf_folders

selected_pdfs = st.sidebar.multiselect(
    "Select OCR folders",
    pdf_folders,
    default=default_selection,
    format_func=lambda p: p.name
)

st.sidebar.info(
    f"Processed Jobs: {len(processed_jobs)}\n"
    f"Remaining PDFs: {len(remaining_folders)}\n"
    f"Total PDFs: {len(pdf_folders)}"
)

if not selected_pdfs:
    st.stop()

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
        start_idx = st.number_input("Start Index", 0, 9999, 0)
    with col2:
        end_idx = st.number_input("End Index", 0, 9999, 3)

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
    st.stop()

selected_models = [
    {
        "label": lbl,
        "id": label_to_id[lbl],
    }
    for lbl in selected_model_labels
]

temperature = st.slider("Temperature", 0.0, 1.5, 0.3)
max_tokens = st.slider("Max Tokens", 512, 8192, 3000)

# =====================================================
# EXPERIMENT NAME
# =====================================================

default_set = f"MultiPDF_ABSA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"
set_name = st.text_input("Experiment Set Name", default_set)

# =====================================================
# RUN ENGINE
# =====================================================

if st.button("🚀 Run Bulk ABSA", type="primary"):

    total_jobs = (
        len(selected_pdfs)
        * len(selected_prompt_names)
        * len(selected_models)
    )

    job_idx = 0
    progress = st.progress(0)
    status = st.empty()
    saved_files = []

    for pdf in selected_pdfs:

        pages_dir = pdf / "pages"
        page_files = sorted(pages_dir.glob("*.md"))

        if not page_files:
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
                model_label = model_cfg["label"]
                model_id = model_cfg["id"]

                job_key = (pdf.name, prompt_name, model_label)

                if process_mode == "Process Only Remaining" and job_key in processed_jobs:
                    progress.progress(job_idx / total_jobs)
                    continue

                status.info(f"{pdf.name} | {prompt_name} | {model_label}")

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

                    fname = f"absa_{ts}_{safe_name(pdf.name)}_{safe_name(prompt_name)}_{safe_name(model_label)}.json"
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
                    st.error(f"{pdf.name} failed: {e}")

                progress.progress(job_idx / total_jobs)
                time.sleep(0.05)

    # Update registry
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

    st.success("✅ Bulk ABSA Completed")
    st.json(saved_files)
