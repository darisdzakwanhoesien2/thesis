import streamlit as st
from pathlib import Path
import json
import pandas as pd

# =====================================================
# PATH SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"
REGISTRY_PATH = LOGS_DIR / "registry.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📊 ABSA Experiment Results Viewer")

st.caption(f"Logs directory: {LOGS_DIR}")

# =====================================================
# LOAD REGISTRY
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ registry.json not found in logs/")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

if "sets" not in registry or not registry["sets"]:
    st.error("❌ No experiment sets found in registry.json")
    st.stop()

set_names = list(registry["sets"].keys())

# =====================================================
# SELECT EXPERIMENT SET
# =====================================================

st.sidebar.header("🧪 Experiment Sets")

selected_set = st.sidebar.selectbox("Select Result Set", set_names)

log_files = registry["sets"][selected_set]

st.sidebar.success(f"{len(log_files)} runs in this set")

# =====================================================
# LOAD LOG FILES
# =====================================================

runs = []

missing = []

for fname in log_files:
    path = LOGS_DIR / fname
    if not path.exists():
        missing.append(fname)
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        data["_file"] = fname
        runs.append(data)

if missing:
    st.warning(f"⚠️ Missing log files: {missing}")

if not runs:
    st.error("❌ No valid log files loaded.")
    st.stop()

# =====================================================
# SUMMARY TABLE
# =====================================================

st.subheader("📋 Run Summary")

summary_rows = []

for r in runs:
    summary_rows.append({
        "file": r["_file"],
        "model": r.get("model"),
        "prompt": r.get("prompt_file"),
        "pages": len(r.get("pages", [])),
        "temperature": r.get("temperature"),
        "tokens": r.get("max_tokens"),
        "timestamp": r.get("timestamp"),
    })

df = pd.DataFrame(summary_rows)
st.dataframe(df, use_container_width=True)

# =====================================================
# RUN-BY-RUN VIEW
# =====================================================

st.subheader("🔍 Detailed Outputs")

for idx, r in enumerate(runs, start=1):

    with st.expander(f"Run {idx} — {r['_file']}"):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### ⚙️ Metadata")
            st.json({
                "model": r.get("model"),
                "prompt_file": r.get("prompt_file"),
                "pages": r.get("pages"),
                "temperature": r.get("temperature"),
                "max_tokens": r.get("max_tokens"),
            })

            st.markdown("### 🧠 Prompt")
            st.text_area(
                "System Prompt",
                r.get("system_prompt", ""),
                height=220,
                key=f"prompt_{idx}"
            )

        with col2:
            st.markdown("### 🤖 Model Output")

            output_text = r.get("output", "")

            # try parse JSON
            try:
                parsed = json.loads(output_text)
                st.json(parsed)
            except Exception:
                st.code(output_text)

# =====================================================
# OPTIONAL: ASPECT COMPARISON
# =====================================================

st.subheader("📈 Aspect Comparison (Quick View)")

aspect_rows = []

for r in runs:
    try:
        parsed = json.loads(r.get("output", "[]"))
        for item in parsed:
            aspect_rows.append({
                "file": r["_file"],
                "aspect": item.get("aspect"),
                "sentiment": item.get("sentiment"),
                "category": item.get("aspect_category"),
            })
    except Exception:
        pass

if aspect_rows:
    df_aspect = pd.DataFrame(aspect_rows)
    st.dataframe(df_aspect, use_container_width=True)
else:
    st.info("No structured JSON detected for aspect comparison.")
