import streamlit as st
from pathlib import Path
import json
import pandas as pd
import re
from collections import Counter
import matplotlib.pyplot as plt

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"
REGISTRY_PATH = LOGS_DIR / "registry.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="📊 ABSA Registry Distribution", layout="wide")
st.title("📊 ABSA Experiment Registry — Distribution Analysis")

st.caption(f"Source: {REGISTRY_PATH}")

# =====================================================
# LOAD REGISTRY
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ logs/registry.json not found.")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

sets = registry.get("sets", {})

if not sets:
    st.warning("Registry is empty.")
    st.stop()

# =====================================================
# SUMMARY TABLE
# =====================================================

summary_rows = []

for set_name, files in sets.items():
    summary_rows.append({
        "Set": set_name,
        "Runs": len(files),
        "Empty": len(files) == 0,
    })

summary_df = pd.DataFrame(summary_rows)

st.subheader("📋 Set Overview")
st.dataframe(summary_df, use_container_width=True)

# =====================================================
# SELECT SET
# =====================================================

st.divider()
st.subheader("🔍 Detailed Distribution")

set_names = list(sets.keys())

selected_set = st.selectbox("Select experiment set", set_names)

files = sets[selected_set]

st.write(f"**Total runs:** {len(files)}")

if not files:
    st.warning("This set contains no experiment files.")
    st.stop()

# =====================================================
# PARSING HELPERS
# =====================================================

def parse_prompt(fname):
    if "zero_shot" in fname:
        return "zero_shot"
    if "few_shot" in fname:
        return "few_shot"
    if "cot" in fname:
        return "cot"
    return "unknown"

def parse_model(fname):
    # Extract model between prompt and (Free)
    # fallback: detect known keywords
    known = [
        "Mistral", "DeepSeek", "Qwen", "Nemotron", "LLaMA", "Gemini"
    ]
    for k in known:
        if k.lower() in fname.lower():
            return k
    return "Other"

# =====================================================
# BUILD DISTRIBUTION DF
# =====================================================

rows = []

for f in files:
    rows.append({
        "file": f,
        "prompt": parse_prompt(f),
        "model": parse_model(f),
    })

df = pd.DataFrame(rows)

st.subheader("🗂 File Table")
st.dataframe(df, use_container_width=True)

# =====================================================
# DISTRIBUTIONS
# =====================================================

col1, col2 = st.columns(2)

# -------- Prompt Distribution --------

prompt_counts = df["prompt"].value_counts()

with col1:
    st.markdown("### 🧪 Prompt Strategy Distribution")
    fig = plt.figure()
    prompt_counts.plot(kind="bar")
    st.pyplot(fig)

    st.dataframe(
        prompt_counts.rename("count").reset_index().rename(columns={"index": "prompt"}),
        use_container_width=True,
    )

# -------- Model Distribution --------

model_counts = df["model"].value_counts()

with col2:
    st.markdown("### 🤖 Model Distribution")
    fig = plt.figure()
    model_counts.plot(kind="bar")
    st.pyplot(fig)

    st.dataframe(
        model_counts.rename("count").reset_index().rename(columns={"index": "model"}),
        use_container_width=True,
    )

# =====================================================
# CROSS TAB
# =====================================================

st.divider()
st.subheader("📊 Prompt × Model Cross Distribution")

pivot = pd.pivot_table(
    df,
    index="model",
    columns="prompt",
    values="file",
    aggfunc="count",
    fill_value=0,
)

st.dataframe(pivot, use_container_width=True)

# =====================================================
# DOWNLOAD TABLE
# =====================================================

st.download_button(
    "⬇ Download Distribution Table (CSV)",
    data=df.to_csv(index=False),
    file_name="registry_distribution.csv",
    mime="text/csv",
)
