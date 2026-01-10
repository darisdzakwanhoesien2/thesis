import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os
import json
import datetime
import time
import pandas as pd
import math

from services.openrouter_client import call_openrouter

# =====================================================
# PATH + ENV
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATA_PATH = BASE_DIR / "data" / "Dataset.csv"

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

REGISTRY_PATH = LOGS_DIR / "registry.json"

# =====================================================
# MODEL CONTEXT WINDOWS
# =====================================================

MODEL_CONTEXT = {
    "xiaomi/mimo-v2-flash:free": 262_144,
    "mistralai/devstral-2512:free": 262_144,
    "tngtech/deepseek-r1t2-chimera:free": 163_840,
    "kwaipilot/kat-coder-pro:free": 256_000,
    "tngtech/deepseek-r1t-chimera:free": 163_840,
    "qwen/qwen3-coder:free": 262_000,
    "z-ai/glm-4.5-air:free": 131_072,
    "nvidia/nemotron-3-nano-30b-a3b:free": 256_000,
    "deepseek/deepseek-r1-0528:free": 163_840,
    "nvidia/nemotron-nano-12b-v2-vl:free": 128_000,
    "tngtech/tng-r1t-chimera:free": 163_840,
    "google/gemma-3-27b-it:free": 131_072,
    "meta-llama/llama-3.3-70b-instruct:free": 131_072,
    "openai/gpt-oss-120b:free": 131_072,
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free": 32_768,
    "google/gemini-2.0-flash-exp:free": 1_048_576,
    "nousresearch/hermes-3-llama-3.1-405b:free": 131_072,
    "openai/gpt-oss-20b:free": 131_072,
    "mistralai/mistral-7b-instruct:free": 32_768,
    "mistralai/mistral-small-3.1-24b-instruct:free": 128_000,
    "meta-llama/llama-3.1-405b-instruct:free": 131_072,
    "arcee-ai/trinity-mini:free": 131_072,
    "nvidia/nemotron-nano-9b-v2:free": 128_000,
    "meta-llama/llama-3.2-3b-instruct:free": 131_072,
    "qwen/qwen3-4b:free": 40_960,
    "qwen/qwen-2.5-vl-7b-instruct:free": 32_768,
    "google/gemma-3n-e2b-it:free": 8_192,
    "google/gemma-3-4b-it:free": 32_768,
    "google/gemma-3-12b-it:free": 32_768,
    "google/gemma-3n-e4b-it:free": 8_192,
    "allenai/molmo-2-8b:free": 36_864,
    "moonshotai/kimi-k2:free": 32_768,
}

# =====================================================
# TOKEN ESTIMATION + SPLIT
# =====================================================

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def split_text_by_tokens(text, max_tokens):
    approx_chars = max_tokens * 4
    chunks = []
    for i in range(0, len(text), approx_chars):
        chunks.append(text[i:i + approx_chars])
    return chunks


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📦 Bulk Pages ABSA — CSV Source (Context-Aware)")

# =====================================================
# LOAD CSV
# =====================================================

@st.cache_data
def load_csv(path):
    return pd.read_csv(path)

if not DATA_PATH.exists():
    st.error("❌ data/Dataset.csv not found.")
    st.stop()

df = load_csv(DATA_PATH)

# =====================================================
# PROMPTS
# =====================================================

st.sidebar.header("🧠 Prompt Methods")

PROMPT_DIR = BASE_DIR / "prompts"
prompt_files = sorted(PROMPT_DIR.glob("*.md"))
prompt_map = {p.name: p for p in prompt_files}

selected_prompt_names = st.sidebar.multiselect(
    "Select Prompt Methods",
    list(prompt_map.keys()),
    default=[p for p in prompt_map if "zero" in p.lower()]
)

# =====================================================
# DATA SELECTION
# =====================================================

st.sidebar.header("📂 Data")

markdown_cols = [c for c in df.columns if c.startswith("markdown") or c == "cleaned_markdown"]

md_col = st.sidebar.selectbox("Markdown Column", markdown_cols)

filenames = sorted(df["filename"].astype(str).unique())
selected_file = st.sidebar.selectbox("Filename", filenames)

df_file = df[df["filename"] == selected_file]

min_i = int(df_file["index"].min())
max_i = int(df_file["index"].max())

start_idx = st.number_input("Start Index", min_i, max_i, min_i)
end_idx = st.number_input("End Index", min_i, max_i, min(min_i + 2, max_i))

df_sel = df_file[(df_file["index"] >= start_idx) & (df_file["index"] <= end_idx)]

# =====================================================
# MODEL
# =====================================================

MODEL_OPTIONS = list(MODEL_CONTEXT.keys())
model_name = st.selectbox("Model", MODEL_OPTIONS)

temperature = st.slider("Temperature", 0.0, 1.5, 0.3)
max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# =====================================================
# PREVIEW + TOKEN INFO
# =====================================================

combined_text = ""
for _, r in df_sel.iterrows():
    combined_text += f"\n\n--- PAGE {r['index']} ---\n{str(r.get(md_col, ''))}\n"

prompt_tokens_est = estimate_tokens(combined_text)
context_window = MODEL_CONTEXT.get(model_name, 0)
usage_pct = (prompt_tokens_est / context_window * 100) if context_window else 0

st.metric("Estimated Prompt Tokens", f"{prompt_tokens_est:,}")
st.metric("Model Context Window", f"{context_window:,}")
st.metric("Context Usage", f"{usage_pct:.2f}%")

if usage_pct > 80:
    st.warning("⚠️ Prompt exceeds 80% of model context. Auto-splitting will be applied.")

# =====================================================
# RUN
# =====================================================

if st.button("🚀 Run Multi-Method ABSA", type="primary"):

    # auto-split if needed
    max_prompt_tokens = int(context_window * 0.75)
    chunks = (
        split_text_by_tokens(combined_text, max_prompt_tokens)
        if prompt_tokens_est > max_prompt_tokens else [combined_text]
    )

    saved_files = []
    progress = st.progress(0.0)

    for i, prompt_name in enumerate(selected_prompt_names, start=1):

        system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

        chunk_outputs = []
        chunk_latencies = []
        t_start = time.time()

        for ci, chunk in enumerate(chunks, start=1):

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk},
            ]

            t0 = time.time()
            output = call_openrouter(
                messages=messages,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency = round(time.time() - t0, 3)

            chunk_outputs.append(output)
            chunk_latencies.append(latency)

        total_duration = round(time.time() - t_start, 3)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        log = {
            "timestamp": ts,
            "filename": selected_file,
            "rows_used": df_sel["index"].tolist(),
            "markdown_column": md_col,
            "prompt_file": prompt_name,
            "model": model_name,
            "estimated_prompt_tokens": prompt_tokens_est,
            "model_context_window": context_window,
            "chunk_count": len(chunks),
            "chunk_latencies_sec": chunk_latencies,
            "total_duration_sec": total_duration,
            "output": "\n\n".join(chunk_outputs),
        }

        fname = f"bulk_absa_{ts}_{prompt_name.replace('.md','')}.json"
        with open(LOGS_DIR / fname, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2)

        saved_files.append(fname)
        progress.progress(i / len(selected_prompt_names))

    # registry
    if REGISTRY_PATH.exists():
        registry = json.load(open(REGISTRY_PATH))
    else:
        registry = {"sets": {}}

    set_name = f"{selected_file} — {md_col}"
    registry["sets"][set_name] = saved_files
    json.dump(registry, open(REGISTRY_PATH, "w"), indent=2)

    st.success("✅ Completed")
    st.json(saved_files)


# import streamlit as st
# from pathlib import Path
# from dotenv import load_dotenv
# import os
# import json
# import datetime
# import time
# import pandas as pd

# from services.openrouter_client import call_openrouter

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# load_dotenv(BASE_DIR / ".env")

# DATA_PATH = BASE_DIR / "data" / "Dataset.csv"

# LOGS_DIR = BASE_DIR / "logs"
# LOGS_DIR.mkdir(exist_ok=True)

# REGISTRY_PATH = LOGS_DIR / "registry.json"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("📦 Bulk Pages ABSA — CSV Markdown Source (Multi-Method)")

# st.caption(f"Project root: {BASE_DIR}")
# st.caption(f"Dataset: {DATA_PATH}")

# # =====================================================
# # LOAD CSV
# # =====================================================

# @st.cache_data
# def load_csv(path):
#     return pd.read_csv(path)

# if not DATA_PATH.exists():
#     st.error("❌ data/Dataset.csv not found.")
#     st.stop()

# try:
#     df = load_csv(DATA_PATH)
# except Exception as e:
#     st.error(f"❌ Failed to load CSV: {e}")
#     st.stop()

# st.success(f"Loaded {len(df)} rows")

# # =====================================================
# # REQUIRED COLUMNS
# # =====================================================

# REQUIRED = ["filename", "index"]
# missing = [c for c in REQUIRED if c not in df.columns]

# if missing:
#     st.error(f"Missing required columns: {missing}")
#     st.stop()

# # Normalize types
# df["filename"] = df["filename"].astype(str)

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

# preview_prompt = prompt_map[selected_prompt_names[0]].read_text(encoding="utf-8")

# st.text_area(
#     "📝 Preview Prompt (first selected, editable copy only)",
#     value=preview_prompt,
#     height=220
# )

# # =====================================================
# # MARKDOWN COLUMN SELECTION
# # =====================================================

# st.sidebar.header("📝 Markdown Source")

# markdown_cols = [
#     c for c in df.columns
#     if c.startswith("markdown") or c == "cleaned_markdown"
# ]

# if not markdown_cols:
#     st.sidebar.error("❌ No markdown columns found in CSV.")
#     st.stop()

# md_col = st.sidebar.selectbox(
#     "Markdown Column",
#     markdown_cols,
#     index=markdown_cols.index("cleaned_markdown")
#     if "cleaned_markdown" in markdown_cols else 0
# )

# # =====================================================
# # FILE SELECTION
# # =====================================================

# st.sidebar.header("📂 Document Selection")

# filenames = sorted(df["filename"].unique())

# selected_file = st.sidebar.selectbox("Filename", filenames)

# df_file = df[df["filename"] == selected_file]

# if df_file.empty:
#     st.error("No rows for selected filename.")
#     st.stop()

# # =====================================================
# # PAGE RANGE (USING index COLUMN)
# # =====================================================

# st.subheader("🔢 Select Page Range (CSV index field)")

# min_i = int(df_file["index"].min())
# max_i = int(df_file["index"].max())

# col1, col2 = st.columns(2)

# with col1:
#     start_idx = st.number_input(
#         "Start Index",
#         min_value=min_i,
#         max_value=max_i,
#         value=min_i,
#         step=1
#     )

# with col2:
#     end_idx = st.number_input(
#         "End Index",
#         min_value=min_i,
#         max_value=max_i,
#         value=min(min_i + 2, max_i),
#         step=1
#     )

# if end_idx < start_idx:
#     st.warning("End index must be >= start index.")
#     st.stop()

# df_sel = df_file[
#     (df_file["index"] >= start_idx) &
#     (df_file["index"] <= end_idx)
# ].sort_values("index")

# st.success(f"Selected {len(df_sel)} pages")

# # =====================================================
# # PREVIEW
# # =====================================================

# with st.expander("👀 Preview Combined Markdown"):
#     preview = ""
#     for _, r in df_sel.iterrows():
#         txt = str(r.get(md_col, ""))[:800]
#         preview += f"\n\n--- PAGE {r['index']} ---\n{txt}\n"
#     st.text_area("Preview", preview, height=350)

# # =====================================================
# # MODEL SETTINGS
# # =====================================================

# st.subheader("🤖 Model Settings")

# # MODEL_OPTIONS = [
# #     "mistralai/mistral-7b-instruct",
# #     "google/gemma-2b-it",
# #     "deepseek/deepseek-r1",
# # ]

# MODEL_OPTIONS = [
#     "xiaomi/mimo-v2-flash:free",
#     "mistralai/devstral-2512:free",
#     "tngtech/deepseek-r1t2-chimera:free",
#     "kwaipilot/kat-coder-pro:free",
#     "tngtech/deepseek-r1t-chimera:free",
#     "qwen/qwen3-coder:free",
#     "z-ai/glm-4.5-air:free",
#     "nvidia/nemotron-3-nano-30b-a3b:free",
#     "deepseek/deepseek-r1-0528:free",
#     "nvidia/nemotron-nano-12b-v2-vl:free",
#     "tngtech/tng-r1t-chimera:free",
#     "google/gemma-3-27b-it:free",
#     "meta-llama/llama-3.3-70b-instruct:free",
#     "openai/gpt-oss-120b:free",
#     "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
#     "google/gemini-2.0-flash-exp:free",
#     "nousresearch/hermes-3-llama-3.1-405b:free",
#     "openai/gpt-oss-20b:free",
#     "mistralai/mistral-7b-instruct:free",
#     "mistralai/mistral-small-3.1-24b-instruct:free",
#     "meta-llama/llama-3.1-405b-instruct:free",
#     "arcee-ai/trinity-mini:free",
#     "nvidia/nemotron-nano-9b-v2:free",
#     "meta-llama/llama-3.2-3b-instruct:free",
#     "qwen/qwen3-4b:free",
#     "qwen/qwen-2.5-vl-7b-instruct:free",
#     "google/gemma-3n-e2b-it:free",
#     "google/gemma-3-4b-it:free",
#     "google/gemma-3-12b-it:free",
#     "google/gemma-3n-e4b-it:free",
#     "allenai/molmo-2-8b:free",
#     "moonshotai/kimi-k2:free",
# ]


# model_name = st.selectbox("Model", MODEL_OPTIONS)

# temperature = st.slider("Temperature", 0.0, 1.5, 0.3, 0.05)
# max_tokens = st.slider("Max Output Tokens", 512, 4096, 3000, 128)

# # =====================================================
# # EXPERIMENT SET NAME
# # =====================================================

# st.subheader("🧪 Experiment Set")

# default_set_name = f"{selected_file} — {md_col} — Prompt Comparison"

# set_name = st.text_input("Experiment Set Name", value=default_set_name)

# # =====================================================
# # RUN MULTI-METHOD EXPERIMENT
# # =====================================================

# if st.button("🚀 Run Multi-Method ABSA", type="primary"):

#     # -------------------------------------------------
#     # COMBINE MARKDOWN FROM CSV
#     # -------------------------------------------------
#     combined_text = ""

#     for _, r in df_sel.iterrows():
#         txt = str(r.get(md_col, ""))
#         combined_text += f"\n\n--- PAGE {r['index']} ---\n{txt}\n"

#     combined_text = combined_text[:24000]  # token safety

#     saved_files = []

#     progress = st.progress(0.0)
#     status = st.empty()

#     # -------------------------------------------------
#     # RUN EACH PROMPT
#     # -------------------------------------------------
#     for i, prompt_name in enumerate(selected_prompt_names, start=1):

#         status.info(f"Running {prompt_name} ({i}/{len(selected_prompt_names)})")

#         system_prompt = prompt_map[prompt_name].read_text(encoding="utf-8")

#         messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": combined_text},
#         ]

#         try:
#             output = call_openrouter(
#                 messages=messages,
#                 model=model_name,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#             )

#             ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

#             log = {
#                 "timestamp": ts,
#                 "filename": selected_file,
#                 "page_index_range": [int(start_idx), int(end_idx)],
#                 "markdown_column": md_col,
#                 "rows_used": df_sel["index"].tolist(),
#                 "prompt_file": prompt_name,
#                 "model": model_name,
#                 "temperature": temperature,
#                 "max_tokens": max_tokens,
#                 "system_prompt": system_prompt,
#                 "output": output,
#             }

#             fname = f"bulk_absa_{ts}_{prompt_name.replace('.md','')}.json"
#             log_path = LOGS_DIR / fname

#             with open(log_path, "w", encoding="utf-8") as f:
#                 json.dump(log, f, indent=2)

#             saved_files.append(fname)

#         except Exception as e:
#             st.error(f"{prompt_name} failed: {e}")

#         progress.progress(i / len(selected_prompt_names))
#         time.sleep(0.4)

#     # -------------------------------------------------
#     # UPDATE REGISTRY.JSON
#     # -------------------------------------------------

#     if REGISTRY_PATH.exists():
#         with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#             registry = json.load(f)
#     else:
#         registry = {"sets": {}}

#     registry.setdefault("sets", {})
#     registry["sets"][set_name] = saved_files

#     with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
#         json.dump(registry, f, indent=2)

#     st.success("✅ Experiment completed")
#     st.success(f"Saved {len(saved_files)} runs into set:")
#     st.code(set_name)

#     st.write("Files:")
#     st.json(saved_files)
