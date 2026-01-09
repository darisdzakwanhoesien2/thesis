import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import datetime

from services.openrouter_client import call_openrouter

# =====================================================
# SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

st.set_page_config(layout="wide")
st.title("📦 Bulk Pages ABSA — Multi-Page Context")

# =====================================================
# PROMPT TEMPLATES
# =====================================================

PROMPT_DIR = BASE_DIR / "prompts"

if not PROMPT_DIR.exists():
    st.error("❌ prompts/ directory not found.")
    st.stop()

prompt_files = sorted(PROMPT_DIR.glob("*.md"))

if not prompt_files:
    st.error("❌ No .md prompt files found in prompts/")
    st.stop()

prompt_map = {p.name: p for p in prompt_files}

# =====================================================
# DATA SELECTION
# =====================================================

outputs_root = BASE_DIR / "outputs"

if not outputs_root.exists():
    st.error("❌ outputs/ directory not found.")
    st.stop()

pdf_folders = [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]

if not pdf_folders:
    st.error("❌ No *_pdf folders found in outputs/")
    st.stop()

selected_pdf = st.selectbox("📄 PDF Folder", pdf_folders, format_func=lambda p: p.name)

pages_dir = selected_pdf / "pages"

if not pages_dir.exists():
    st.error("❌ pages/ folder not found in selected PDF.")
    st.stop()

page_files = sorted(pages_dir.glob("*.md"))

if not page_files:
    st.error("❌ No page_XXX.md files found.")
    st.stop()

st.caption(f"📑 {len(page_files)} pages detected")

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
# PROMPT SELECTION
# =====================================================

st.subheader("🧠 Prompt Template")

selected_prompt_name = st.selectbox("Prompt file (.md)", list(prompt_map.keys()))
system_prompt = prompt_map[selected_prompt_name].read_text(encoding="utf-8")

system_prompt = st.text_area(
    "System Prompt (editable)",
    value=system_prompt,
    height=260
)

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

model_name = st.selectbox(
    "Model",
    [
        "mistralai/mistral-7b-instruct",
        "google/gemma-2b-it",
        "deepseek/deepseek-r1",
    ]
)

temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# =====================================================
# RUN BULK LLM
# =====================================================

if st.button("🚀 Run Bulk LLM", type="primary"):

    combined_text = ""

    for p in selected_pages:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

    if len(combined_text) > 20000:
        st.warning("⚠️ Large input — consider reducing page range.")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": combined_text[:24000]},
    ]

    with st.spinner("Calling LLM with multi-page context..."):
        try:
            output = call_openrouter(
                messages=messages,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            st.subheader("✅ Model Output")
            st.code(output, language="json")

            # =====================================================
            # SAVE LOG
            # =====================================================

            logs_dir = BASE_DIR / "logs"
            logs_dir.mkdir(exist_ok=True)

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            log = {
                "timestamp": ts,
                "pdf": selected_pdf.name,
                "pages": [p.name for p in selected_pages],
                "prompt_file": selected_prompt_name,
                "model": model_name,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
                "output": output,
            }

            log_path = logs_dir / f"bulk_absa_{ts}.json"
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log, f, indent=2)

            st.success(f"Saved: {log_path.name}")

            with st.expander("📨 Sent Messages (Debug)"):
                st.json(messages)

        except Exception as e:
            st.error(str(e))


# import streamlit as st
# from pathlib import Path
# from dotenv import load_dotenv
# import os
# import json
# import datetime

# from services.openrouter_client import call_openrouter

# # =====================================================
# # SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# load_dotenv(BASE_DIR / ".env")

# st.set_page_config(layout="wide")
# st.title("📦 Bulk Pages ABSA — Multi-Page Context")

# # =====================================================
# # DATA SELECTION
# # =====================================================

# outputs_root = BASE_DIR / "outputs"
# pdf_folders = [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]

# selected_pdf = st.selectbox("PDF Folder", pdf_folders, format_func=lambda p: p.name)
# pages_dir = selected_pdf / "pages"
# page_files = sorted(pages_dir.glob("*.md"))

# st.caption(f"{len(page_files)} pages detected")

# # =====================================================
# # PAGE RANGE
# # =====================================================

# col1, col2 = st.columns(2)
# with col1:
#     start_idx = st.number_input("Start Page Index", 0, len(page_files)-1, 0)
# with col2:
#     end_idx = st.number_input("End Page Index", 0, len(page_files)-1, min(5, len(page_files)-1))

# selected_pages = page_files[start_idx:end_idx+1]

# st.success(f"Selected {len(selected_pages)} pages")

# # =====================================================
# # PREVIEW
# # =====================================================

# with st.expander("Preview Combined Text"):
#     combined_preview = "\n\n".join(
#         [p.read_text(encoding="utf-8", errors="ignore")[:1000] for p in selected_pages]
#     )
#     st.text_area("Preview", combined_preview, height=300)

# # =====================================================
# # PROMPT
# # =====================================================

# system_prompt = st.text_area("System Prompt", height=220, value="""
# You are an ESG document analysis model.

# Given multiple consecutive pages from a sustainability report:

# 1. Extract ESG aspects across pages
# 2. Merge duplicate aspects
# 3. Provide aggregated sentiment
# 4. Provide strongest evidence sentence

# Return JSON list:
# [{aspect, sentiment, evidence, page_refs, category}]
# """)

# # =====================================================
# # RUN BULK LLM
# # =====================================================

# if st.button("🚀 Run Bulk LLM"):

#     combined_text = ""
#     for p in selected_pages:
#         txt = p.read_text(encoding="utf-8", errors="ignore")
#         combined_text += f"\n\n--- PAGE {p.name} ---\n{txt}\n"

#     if len(combined_text) > 15000:
#         st.warning("Large input — consider reducing page range")

#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": combined_text[:20000]},
#     ]

#     with st.spinner("Calling LLM with multi-page context..."):
#         output = call_openrouter(messages, "mistralai/mistral-7b-instruct", 0.3, 3500)

#     st.subheader("Model Output")
#     st.code(output, language="json")

#     # =====================================================
#     # SAVE LOG
#     # =====================================================

#     logs_dir = BASE_DIR / "logs"
#     logs_dir.mkdir(exist_ok=True)

#     ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

#     log = {
#         "pdf": selected_pdf.name,
#         "pages": [p.name for p in selected_pages],
#         "prompt": system_prompt,
#         "output": output,
#     }

#     log_path = logs_dir / f"bulk_absa_{ts}.json"
#     with open(log_path, "w") as f:
#         json.dump(log, f, indent=2)

#     st.success(f"Saved: {log_path.name}")
