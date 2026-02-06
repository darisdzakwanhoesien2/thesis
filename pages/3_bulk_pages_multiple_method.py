import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import datetime
import time

from services.openrouter_client import call_openrouter

# =====================================================
# PATH SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

REGISTRY_PATH = LOGS_DIR / "registry.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📦 Bulk Pages ABSA — Multi-Method Experiment Runner")

st.caption(f"Project root: {BASE_DIR}")

# =====================================================
# PROMPT TEMPLATES
# =====================================================

st.sidebar.header("🧠 Prompt Methods")

PROMPT_DIR = BASE_DIR / "prompts"

if not PROMPT_DIR.exists():
    st.sidebar.error("❌ prompts/ directory not found.")
    st.stop()

prompt_files = sorted(PROMPT_DIR.glob("*.md"))

if not prompt_files:
    st.sidebar.error("❌ No .md prompt files found in prompts/")
    st.stop()

prompt_map = {p.name: p for p in prompt_files}

selected_prompt_names = st.sidebar.multiselect(
    "Select Prompt Methods",
    list(prompt_map.keys()),
    default=[p for p in prompt_map if "zero" in p.lower()]
)

if not selected_prompt_names:
    st.warning("Select at least one prompt method.")
    st.stop()

# Preview first selected prompt
preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")

system_prompt_preview = st.text_area(
    "📝 Preview Prompt (first selected, editable copy only)",
    value=preview_prompt,
    height=220
)

# =====================================================
# DATA SELECTION
# =====================================================

st.sidebar.header("📂 PDF Selection")

outputs_root = BASE_DIR / "outputs"

if not outputs_root.exists():
    st.sidebar.error("❌ outputs/ directory not found.")
    st.stop()

pdf_folders = sorted([
    p for p in outputs_root.iterdir()
    if p.is_dir() and p.name.endswith("_pdf")
])

if not pdf_folders:
    st.sidebar.error("❌ No *_pdf folders found in outputs/")
    st.stop()

selected_pdf = st.sidebar.selectbox(
    "PDF Folder",
    pdf_folders,
    format_func=lambda p: p.name
)

pages_dir = selected_pdf / "pages"

if not pages_dir.exists():
    st.error("❌ pages/ folder not found in selected PDF.")
    st.stop()

page_files = sorted(pages_dir.glob("*.md"))

if not page_files:
    st.error("❌ No page_XXX.md files found.")
    st.stop()

st.sidebar.success(f"{len(page_files)} pages found")

# =====================================================
# PAGE RANGE
# =====================================================

st.subheader("🔢 Select Page Range")

col1, col2 = st.columns(2)

with col1:
    start_idx = st.number_input(
        "Start Page Index",
        min_value=0,
        max_value=len(page_files) - 1,
        value=0,
        step=1
    )

with col2:
    end_idx = st.number_input(
        "End Page Index",
        min_value=0,
        max_value=len(page_files) - 1,
        value=min(3, len(page_files) - 1),
        step=1
    )

if end_idx < start_idx:
    st.warning("End index must be >= start index.")
    st.stop()

selected_pages = page_files[start_idx:end_idx + 1]
st.success(f"Selected {len(selected_pages)} pages")

# =====================================================
# PREVIEW
# =====================================================

with st.expander("👀 Preview Combined Text"):
    preview = "\n\n".join([
        f"--- {p.name} ---\n{p.read_text(encoding='utf-8', errors='ignore')[:800]}"
        for p in selected_pages
    ])
    st.text_area("Preview", preview, height=350)

# =====================================================
# MODEL SETTINGS
# =====================================================

st.subheader("🤖 Model Settings")

MODEL_OPTIONS = [
    "mistralai/mistral-7b-instruct",
    "google/gemma-2b-it",
    "deepseek/deepseek-r1",
]

model_name = st.selectbox("Model", MODEL_OPTIONS)

temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# =====================================================
# EXPERIMENT SET NAME
# =====================================================

st.subheader("🧪 Experiment Set")

default_set_name = f"{selected_pdf.name} — Prompt Comparison"

set_name = st.text_input("Experiment Set Name", value=default_set_name)

# =====================================================
# RUN MULTI-METHOD EXPERIMENT
# =====================================================

if st.button("🚀 Run Multi-Method ABSA", type="primary"):

    combined_text = ""
    for p in selected_pages:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

    combined_text = combined_text[:24000]

    saved_files = []

    progress = st.progress(0)
    status = st.empty()

    for i, prompt_name in enumerate(selected_prompt_names, start=1):

        status.info(f"Running {prompt_name} ({i}/{len(selected_prompt_names)})")

        system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": combined_text},
        ]

        try:
            output = call_openrouter(
                messages=messages,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            log = {
                "timestamp": ts,
                "pdf": selected_pdf.name,
                "pages": [p.name for p in selected_pages],
                "prompt_file": prompt_name,
                "model": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
                "output": output,
            }

            fname = f"bulk_absa_{ts}_{prompt_name.replace('.md','')}.json"
            log_path = LOGS_DIR / fname

            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log, f, indent=2)

            saved_files.append(fname)

        except Exception as e:
            st.error(f"{prompt_name} failed: {e}")

        progress.progress(i / len(selected_prompt_names))
        time.sleep(0.5)

    # =====================================================
    # UPDATE REGISTRY.JSON
    # =====================================================

    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"sets": {}}

    registry.setdefault("sets", {})
    registry["sets"][set_name] = saved_files

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    st.success("✅ Experiment completed")
    st.success(f"Saved {len(saved_files)} runs into set:")
    st.code(set_name)

    st.write("Files:")
    st.json(saved_files)
