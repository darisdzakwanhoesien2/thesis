import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
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

DATA_DIR = BASE_DIR / "data"
MODELS_PATH = DATA_DIR / "models.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📦 Bulk ABSA — Multi-PDF & Multi-Method Runner")
st.caption(f"Project root: {BASE_DIR}")

# =====================================================
# LOAD MODELS FROM JSON
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
# PROMPT METHODS
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
    default=[p for p in prompt_map if "zero" in p.lower()],
)

if not selected_prompt_names:
    st.warning("Select at least one prompt method.")
    st.stop()

# preview first prompt
preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")
st.text_area("📝 Preview Prompt (first selected)", value=preview_prompt, height=220)

# =====================================================
# MULTI PDF SELECTION
# =====================================================

st.sidebar.header("📂 PDF Selection")

outputs_root = BASE_DIR / "outputs"

if not outputs_root.exists():
    st.sidebar.error("❌ outputs/ directory not found.")
    st.stop()

pdf_folders = sorted(
    [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]
)

if not pdf_folders:
    st.sidebar.error("❌ No *_pdf folders found in outputs/")
    st.stop()

selected_pdfs = st.sidebar.multiselect(
    "Select PDF folders",
    pdf_folders,
    format_func=lambda p: p.name,
)

if not selected_pdfs:
    st.warning("Select at least one PDF folder.")
    st.stop()

# =====================================================
# PAGE MODE
# =====================================================

st.subheader("📄 Page Selection Mode")

page_mode = st.radio(
    "Choose page strategy:",
    ["Specific Page Range", "ALL Pages per PDF"],
)

if page_mode == "Specific Page Range":
    col1, col2 = st.columns(2)
    with col1:
        start_idx = st.number_input("Start Page Index", min_value=0, value=0, step=1)
    with col2:
        end_idx = st.number_input("End Page Index", min_value=0, value=3, step=1)

    if end_idx < start_idx:
        st.warning("End index must be >= start index.")
        st.stop()

# =====================================================
# PREVIEW FIRST PDF
# =====================================================

with st.expander("👀 Preview (First Selected PDF)"):
    first_pdf = selected_pdfs[0]
    pages_dir = first_pdf / "pages"
    page_files = sorted(pages_dir.glob("*.md"))

    if not page_files:
        st.warning("No pages found.")
    else:
        if page_mode == "ALL Pages per PDF":
            preview_pages = page_files[:3]
        else:
            preview_pages = page_files[start_idx : end_idx + 1]

        preview = "\n\n".join(
            [
                f"--- {p.name} ---\n{p.read_text(encoding='utf-8', errors='ignore')[:800]}"
                for p in preview_pages
            ]
        )
        st.text_area("Preview", preview, height=350)

# =====================================================
# MODEL SETTINGS
# =====================================================

st.subheader("🤖 Model Settings")

model_label = st.selectbox("Model", list(label_to_id.keys()))
model_name = label_to_id[model_label]

temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

selected_model_meta = next(m for m in models if m["label"] == model_label)

with st.expander("ℹ️ Model Info"):
    st.json(selected_model_meta)

# =====================================================
# EXPERIMENT SET
# =====================================================

st.subheader("🧪 Experiment Set")

default_set_name = f"MultiPDF_ABSA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"

set_name = st.text_input("Experiment Set Name", value=default_set_name)

# =====================================================
# RUN EXPERIMENT
# =====================================================

if st.button("🚀 Run Multi-PDF Multi-Prompt ABSA", type="primary"):

    saved_files = []

    total_jobs = len(selected_pdfs) * len(selected_prompt_names)
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
            selected_pages = page_files[start_idx : end_idx + 1]

        combined_text = ""
        for p in selected_pages:
            txt = p.read_text(encoding="utf-8", errors="ignore")
            combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

        # soft safety limit (will upgrade to chunking later)
        combined_text = combined_text[:24000]

        for prompt_name in selected_prompt_names:

            job_idx += 1
            status.info(
                f"PDF {pdf_i}/{len(selected_pdfs)} | "
                f"Job {job_idx}/{total_jobs} — {pdf.name} — {prompt_name}"
            )

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
                    "experiment_set": set_name,
                    "pdf": pdf.name,
                    "pages": [p.name for p in selected_pages],
                    "prompt_file": prompt_name,
                    "model": model_name,
                    "model_label": model_label,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "system_prompt": system_prompt,
                    "output": output,
                }

                fname = f"absa_{ts}_{pdf.name}_{prompt_name.replace('.md','')}.json"
                fname = fname.replace(" ", "_")
                log_path = LOGS_DIR / fname

                with open(log_path, "w", encoding="utf-8") as f:
                    json.dump(log, f, indent=2)

                saved_files.append(fname)

            except Exception as e:
                st.error(f"{pdf.name} | {prompt_name} failed: {e}")

            progress.progress(job_idx / total_jobs)
            time.sleep(0.2)

    # =====================================================
    # UPDATE REGISTRY
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

    st.success("✅ Multi-PDF ABSA Experiment Completed")
    st.success(f"Saved {len(saved_files)} runs into set:")
    st.code(set_name)

    st.write("Files:")
    st.json(saved_files)


# import streamlit as st
# from pathlib import Path
# from dotenv import load_dotenv
# import json
# import datetime
# import time

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

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("📦 Bulk ABSA — Multi-PDF & Multi-Method Runner")

# st.caption(f"Project root: {BASE_DIR}")

# # =====================================================
# # LOAD MODELS FROM JSON
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
# # PROMPT METHODS
# # =====================================================

# st.sidebar.header("🧠 Prompt Methods")

# PROMPT_DIR = BASE_DIR / "prompts"

# if not PROMPT_DIR.exists():
#     st.sidebar.error("❌ prompts/ directory not found.")
#     st.stop()

# prompt_files = sorted(PROMPT_DIR.glob("*.md"))

# if not prompt_files:
#     st.sidebar.error("❌ No .md prompt files found in prompts/")
#     st.stop()

# prompt_map = {p.name: p for p in prompt_files}

# selected_prompt_names = st.sidebar.multiselect(
#     "Select Prompt Methods",
#     list(prompt_map.keys()),
#     default=[p for p in prompt_map if "zero" in p.lower()],
# )

# if not selected_prompt_names:
#     st.warning("Select at least one prompt method.")
#     st.stop()

# # preview prompt
# preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")

# st.text_area(
#     "📝 Preview Prompt (first selected)",
#     value=preview_prompt,
#     height=220,
# )

# # =====================================================
# # MULTI PDF SELECTION
# # =====================================================

# st.sidebar.header("📂 PDF Selection")

# outputs_root = BASE_DIR / "outputs"

# if not outputs_root.exists():
#     st.sidebar.error("❌ outputs/ directory not found.")
#     st.stop()

# pdf_folders = sorted(
#     [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]
# )

# if not pdf_folders:
#     st.sidebar.error("❌ No *_pdf folders found in outputs/")
#     st.stop()

# selected_pdfs = st.sidebar.multiselect(
#     "Select PDF folders",
#     pdf_folders,
#     format_func=lambda p: p.name,
# )

# if not selected_pdfs:
#     st.warning("Select at least one PDF folder.")
#     st.stop()

# # =====================================================
# # PAGE MODE
# # =====================================================

# st.subheader("📄 Page Selection Mode")

# page_mode = st.radio(
#     "Choose page strategy:",
#     ["Specific Page Range", "ALL Pages per PDF"],
# )

# if page_mode == "Specific Page Range":
#     col1, col2 = st.columns(2)
#     with col1:
#         start_idx = st.number_input("Start Page Index", min_value=0, value=0, step=1)
#     with col2:
#         end_idx = st.number_input("End Page Index", min_value=0, value=3, step=1)

#     if end_idx < start_idx:
#         st.warning("End index must be >= start index.")
#         st.stop()

# # =====================================================
# # PREVIEW (FIRST PDF)
# # =====================================================

# with st.expander("👀 Preview (First Selected PDF)"):

#     first_pdf = selected_pdfs[0]
#     pages_dir = first_pdf / "pages"
#     page_files = sorted(pages_dir.glob("*.md"))

#     if not page_files:
#         st.warning("No pages found.")
#     else:
#         if page_mode == "ALL Pages per PDF":
#             preview_pages = page_files[:3]
#         else:
#             preview_pages = page_files[start_idx : end_idx + 1]

#         preview = "\n\n".join(
#             [
#                 f"--- {p.name} ---\n{p.read_text(encoding='utf-8', errors='ignore')[:800]}"
#                 for p in preview_pages
#             ]
#         )
#         st.text_area("Preview", preview, height=350)

# # =====================================================
# # MODEL SETTINGS
# # =====================================================

# st.subheader("🤖 Model Settings")

# model_label = st.selectbox("Model", list(label_to_id.keys()))
# model_name = label_to_id[model_label]

# temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
# max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# selected_model_meta = next(m for m in models if m["label"] == model_label)

# with st.expander("ℹ️ Model Info"):
#     st.json(selected_model_meta)

# # =====================================================
# # EXPERIMENT SET
# # =====================================================

# st.subheader("🧪 Experiment Set")

# default_set_name = f"MultiPDF_ABSA_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}"

# set_name = st.text_input("Experiment Set Name", value=default_set_name)

# # =====================================================
# # RUN EXPERIMENT
# # =====================================================

# if st.button("🚀 Run Multi-PDF Multi-Prompt ABSA", type="primary"):

#     saved_files = []

#     total_jobs = len(selected_pdfs) * len(selected_prompt_names)
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

#         # soft context safety
#         combined_text = combined_text[:24000]

#         for prompt_name in selected_prompt_names:

#             job_idx += 1
#             status.info(
#                 f"PDF {pdf_i}/{len(selected_pdfs)} | "
#                 f"Job {job_idx}/{total_jobs} — {pdf.name} — {prompt_name}"
#             )

#             system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

#             messages = [
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": combined_text},
#             ]

#             try:
#                 output = call_openrouter(
#                     messages=messages,
#                     model=model_name,
#                     temperature=temperature,
#                     max_tokens=max_tokens,
#                 )

#                 ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

#                 log = {
#                     "timestamp": ts,
#                     "experiment_set": set_name,
#                     "pdf": pdf.name,
#                     "pages": [p.name for p in selected_pages],
#                     "prompt_file": prompt_name,
#                     "model": model_name,
#                     "model_label": model_label,
#                     "temperature": temperature,
#                     "max_tokens": max_tokens,
#                     "system_prompt": system_prompt,
#                     "output": output,
#                 }

#                 fname = f"absa_{ts}_{pdf.name}_{prompt_name.replace('.md','')}.json"
#                 fname = fname.replace(" ", "_")
#                 log_path = LOGS_DIR / fname

#                 with open(log_path, "w", encoding="utf-8") as f:
#                     json.dump(log, f, indent=2)

#                 saved_files.append(fname)

#             except Exception as e:
#                 st.error(f"{pdf.name} | {prompt_name} failed: {e}")

#             progress.progress(job_idx / total_jobs)
#             time.sleep(0.2)

#     # =====================================================
#     # UPDATE REGISTRY
#     # =====================================================

#     if REGISTRY_PATH.exists():
#         with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#             registry = json.load(f)
#     else:
#         registry = {"sets": {}}

#     registry.setdefault("sets", {})
#     registry["sets"][set_name] = saved_files

#     with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
#         json.dump(registry, f, indent=2)

#     st.success("✅ Multi-PDF ABSA Experiment Completed")
#     st.success(f"Saved {len(saved_files)} runs into set:")
#     st.code(set_name)

#     st.write("Files:")
#     st.json(saved_files)


# import streamlit as st
# from pathlib import Path
# from dotenv import load_dotenv
# import os
# import json
# import datetime
# import time

# from services.openrouter_client import call_openrouter

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# load_dotenv(BASE_DIR / ".env")

# LOGS_DIR = BASE_DIR / "logs"
# LOGS_DIR.mkdir(exist_ok=True)

# REGISTRY_PATH = LOGS_DIR / "registry.json"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("📦 Bulk Pages ABSA — Multi-Method & Multi-PDF Experiment Runner")

# st.caption(f"Project root: {BASE_DIR}")

# # =====================================================
# # PROMPT TEMPLATES
# # =====================================================

# st.sidebar.header("🧠 Prompt Methods")

# PROMPT_DIR = BASE_DIR / "prompts"

# if not PROMPT_DIR.exists():
#     st.sidebar.error("❌ prompts/ directory not found.")
#     st.stop()

# prompt_files = sorted(PROMPT_DIR.glob("*.md"))

# if not prompt_files:
#     st.sidebar.error("❌ No .md prompt files found in prompts/")
#     st.stop()

# prompt_map = {p.name: p for p in prompt_files}

# selected_prompt_names = st.sidebar.multiselect(
#     "Select Prompt Methods",
#     list(prompt_map.keys()),
#     default=[p for p in prompt_map if "zero" in p.lower()]
# )

# if not selected_prompt_names:
#     st.warning("Select at least one prompt method.")
#     st.stop()

# # Preview first selected prompt
# preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")

# system_prompt_preview = st.text_area(
#     "📝 Preview Prompt (first selected, editable copy only)",
#     value=preview_prompt,
#     height=220
# )

# # =====================================================
# # PDF SELECTION (MULTI)
# # =====================================================

# st.sidebar.header("📂 PDF Selection")

# outputs_root = BASE_DIR / "outputs"

# if not outputs_root.exists():
#     st.sidebar.error("❌ outputs/ directory not found.")
#     st.stop()

# pdf_folders = sorted([
#     p for p in outputs_root.iterdir()
#     if p.is_dir() and p.name.endswith("_pdf")
# ])

# if not pdf_folders:
#     st.sidebar.error("❌ No *_pdf folders found in outputs/")
#     st.stop()

# selected_pdfs = st.sidebar.multiselect(
#     "Select PDF folders (multi)",
#     pdf_folders,
#     format_func=lambda p: p.name,
# )

# if not selected_pdfs:
#     st.warning("Select at least one PDF folder.")
#     st.stop()

# # =====================================================
# # PAGE MODE
# # =====================================================

# st.subheader("📄 Page Selection Mode")

# page_mode = st.radio(
#     "Choose how to process pages:",
#     ["Specific Page Range", "ALL Pages per PDF"],
# )

# page_ranges = {}

# if page_mode == "Specific Page Range":
#     st.info("Same page range will be applied to ALL selected PDFs")

#     col1, col2 = st.columns(2)
#     with col1:
#         start_idx = st.number_input("Start Page Index", min_value=0, value=0, step=1)
#     with col2:
#         end_idx = st.number_input("End Page Index", min_value=0, value=3, step=1)

#     if end_idx < start_idx:
#         st.warning("End index must be >= start index.")
#         st.stop()

# # =====================================================
# # PREVIEW (FIRST PDF ONLY)
# # =====================================================

# with st.expander("👀 Preview (First Selected PDF)"):

#     first_pdf = selected_pdfs[0]
#     pages_dir = first_pdf / "pages"
#     page_files = sorted(pages_dir.glob("*.md"))

#     if not page_files:
#         st.warning("No pages found.")
#     else:
#         if page_mode == "ALL Pages per PDF":
#             preview_pages = page_files[:3]
#         else:
#             preview_pages = page_files[start_idx:end_idx + 1]

#         preview = "\n\n".join([
#             f"--- {p.name} ---\n{p.read_text(encoding='utf-8', errors='ignore')[:800]}"
#             for p in preview_pages
#         ])
#         st.text_area("Preview", preview, height=350)

# # =====================================================
# # MODEL SETTINGS
# # =====================================================

# st.subheader("🤖 Model Settings")

# MODEL_OPTIONS = [
#     "mistralai/mistral-7b-instruct",
#     "google/gemma-2b-it",
#     "deepseek/deepseek-r1",
# ]

# model_name = st.selectbox("Model", MODEL_OPTIONS)
# temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
# max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# # =====================================================
# # EXPERIMENT SET
# # =====================================================

# st.subheader("🧪 Experiment Set")

# default_set_name = f"MultiPDF — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

# set_name = st.text_input("Experiment Set Name", value=default_set_name)

# # =====================================================
# # RUN MULTI-PDF + MULTI-PROMPT
# # =====================================================

# if st.button("🚀 Run Multi-PDF Multi-Method ABSA", type="primary"):

#     saved_files = []

#     total_jobs = len(selected_pdfs) * len(selected_prompt_names)
#     job_idx = 0

#     progress = st.progress(0)
#     status = st.empty()

#     for pdf_idx, pdf in enumerate(selected_pdfs, start=1):

#         pages_dir = pdf / "pages"
#         page_files = sorted(pages_dir.glob("*.md"))

#         if not page_files:
#             st.warning(f"Skipping {pdf.name} — no pages found")
#             continue

#         if page_mode == "ALL Pages per PDF":
#             selected_pages = page_files
#         else:
#             selected_pages = page_files[start_idx:end_idx + 1]

#         combined_text = ""
#         for p in selected_pages:
#             txt = p.read_text(encoding="utf-8", errors="ignore")
#             combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

#         combined_text = combined_text[:24000]

#         for prompt_name in selected_prompt_names:

#             job_idx += 1
#             status.info(
#                 f"PDF {pdf_idx}/{len(selected_pdfs)} | "
#                 f"Prompt {job_idx}/{total_jobs} — {pdf.name} — {prompt_name}"
#             )

#             system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

#             messages = [
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": combined_text},
#             ]

#             try:
#                 output = call_openrouter(
#                     messages=messages,
#                     model=model_name,
#                     temperature=temperature,
#                     max_tokens=max_tokens,
#                 )

#                 ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

#                 log = {
#                     "timestamp": ts,
#                     "pdf": pdf.name,
#                     "pages": [p.name for p in selected_pages],
#                     "prompt_file": prompt_name,
#                     "model": model_name,
#                     "temperature": temperature,
#                     "max_tokens": max_tokens,
#                     "system_prompt": system_prompt,
#                     "output": output,
#                 }

#                 fname = f"bulk_absa_{ts}_{pdf.name}_{prompt_name.replace('.md','')}.json"
#                 fname = fname.replace(" ", "_")
#                 log_path = LOGS_DIR / fname

#                 with open(log_path, "w", encoding="utf-8") as f:
#                     json.dump(log, f, indent=2)

#                 saved_files.append(fname)

#             except Exception as e:
#                 st.error(f"{pdf.name} | {prompt_name} failed: {e}")

#             progress.progress(job_idx / total_jobs)
#             time.sleep(0.3)

#     # =====================================================
#     # UPDATE REGISTRY
#     # =====================================================

#     if REGISTRY_PATH.exists():
#         with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#             registry = json.load(f)
#     else:
#         registry = {"sets": {}}

#     registry.setdefault("sets", {})
#     registry["sets"][set_name] = saved_files

#     with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
#         json.dump(registry, f, indent=2)

#     st.success("✅ Multi-PDF Experiment completed")
#     st.success(f"Saved {len(saved_files)} runs into set:")
#     st.code(set_name)

#     st.write("Files:")
#     st.json(saved_files)
