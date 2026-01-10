import streamlit as st
from pathlib import Path
import json
import pandas as pd
import re

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
st.title("📊 ABSA Experiment Results Viewer (Robust JSON Parsing)")

# =====================================================
# UTIL — JSON RECOVERY
# =====================================================

def extract_json_arrays(text):
    """Extract possible JSON arrays from text using bracket matching."""
    arrays = []
    stack = []
    start = None

    for i, ch in enumerate(text):
        if ch == "[":
            if not stack:
                start = i
            stack.append(ch)
        elif ch == "]" and stack:
            stack.pop()
            if not stack and start is not None:
                arrays.append(text[start:i+1])
                start = None

    return arrays


def safe_json_load(text):
    """Try loading best JSON array found in text."""
    arrays = extract_json_arrays(text)

    for arr in reversed(arrays):  # try last (most complete)
        try:
            return json.loads(arr)
        except Exception:
            continue

    return None


def normalize_items(items, file):
    rows = []
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        rows.append({
            "file": file,
            "sentence": it.get("sentence"),
            "aspect": it.get("aspect"),
            "category": it.get("aspect_category"),
            "sentiment": it.get("sentiment"),
            "score": it.get("sentiment_score"),
            "tone": it.get("tone"),
            "confidence": it.get("confidence"),
        })
    return rows


# =====================================================
# LOAD REGISTRY
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ registry.json not found in logs/")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

set_names = list(registry.get("sets", {}).keys())

if not set_names:
    st.error("❌ No experiment sets in registry.json")
    st.stop()

# =====================================================
# SELECT SET
# =====================================================

st.sidebar.header("🧪 Experiment Sets")

selected_set = st.sidebar.selectbox("Select Result Set", set_names)

log_files = registry["sets"][selected_set]
st.sidebar.success(f"{len(log_files)} runs")

# =====================================================
# LOAD LOGS
# =====================================================

runs = []

for fname in log_files:
    path = LOGS_DIR / fname
    if not path.exists():
        st.warning(f"Missing: {fname}")
        continue
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        data["_file"] = fname
        runs.append(data)

if not runs:
    st.error("No valid logs loaded.")
    st.stop()

# =====================================================
# SUMMARY TABLE
# =====================================================

st.subheader("📋 Run Summary")

summary = [{
    "file": r["_file"],
    "model": r.get("model"),
    "prompt": r.get("prompt_file"),
    "pages": len(r.get("pages", [])),
    "temperature": r.get("temperature"),
} for r in runs]

st.dataframe(pd.DataFrame(summary), use_container_width=True)

# =====================================================
# PARSE OUTPUTS
# =====================================================

all_rows = []

st.subheader("🔍 Run Details")

for idx, r in enumerate(runs, start=1):

    raw_output = r.get("output", "")

    parsed = safe_json_load(raw_output)

    with st.expander(f"Run {idx} — {r['_file']}"):

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### ⚙️ Metadata")
            st.json({
                "model": r.get("model"),
                "prompt": r.get("prompt_file"),
                "pages": r.get("pages"),
            })

            st.markdown("### 🧠 Prompt")
            st.text_area(
                "System Prompt",
                r.get("system_prompt", ""),
                height=200,
                key=f"p_{idx}"
            )

        with col2:
            st.markdown("### 🤖 Output")

            if parsed:
                st.success(f"Recovered {len(parsed)} ABSA items")
                st.json(parsed)
                all_rows.extend(normalize_items(parsed, r["_file"]))
            else:
                st.error("Could not parse JSON")
                st.code(raw_output)

# =====================================================
# AGGREGATED TABLE
# =====================================================

st.subheader("📈 Aggregated Aspect Table")

if all_rows:
    df = pd.DataFrame(all_rows)
    st.dataframe(df, use_container_width=True)

    with st.expander("📥 Download CSV"):
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download ABSA Table", csv, "absa_results.csv")

else:
    st.info("No structured ABSA data recovered.")


# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# LOGS_DIR = BASE_DIR / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("📊 ABSA Experiment Results Viewer")

# st.caption(f"Logs directory: {LOGS_DIR}")

# # =====================================================
# # LOAD REGISTRY
# # =====================================================

# if not REGISTRY_PATH.exists():
#     st.error("❌ registry.json not found in logs/")
#     st.stop()

# with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#     registry = json.load(f)

# if "sets" not in registry or not registry["sets"]:
#     st.error("❌ No experiment sets found in registry.json")
#     st.stop()

# set_names = list(registry["sets"].keys())

# # =====================================================
# # SELECT EXPERIMENT SET
# # =====================================================

# st.sidebar.header("🧪 Experiment Sets")

# selected_set = st.sidebar.selectbox("Select Result Set", set_names)

# log_files = registry["sets"][selected_set]

# st.sidebar.success(f"{len(log_files)} runs in this set")

# # =====================================================
# # LOAD LOG FILES
# # =====================================================

# runs = []

# missing = []

# for fname in log_files:
#     path = LOGS_DIR / fname
#     if not path.exists():
#         missing.append(fname)
#         continue

#     with open(path, "r", encoding="utf-8") as f:
#         data = json.load(f)
#         data["_file"] = fname
#         runs.append(data)

# if missing:
#     st.warning(f"⚠️ Missing log files: {missing}")

# if not runs:
#     st.error("❌ No valid log files loaded.")
#     st.stop()

# # =====================================================
# # SUMMARY TABLE
# # =====================================================

# st.subheader("📋 Run Summary")

# summary_rows = []

# for r in runs:
#     summary_rows.append({
#         "file": r["_file"],
#         "model": r.get("model"),
#         "prompt": r.get("prompt_file"),
#         "pages": len(r.get("pages", [])),
#         "temperature": r.get("temperature"),
#         "tokens": r.get("max_tokens"),
#         "timestamp": r.get("timestamp"),
#     })

# df = pd.DataFrame(summary_rows)
# st.dataframe(df, use_container_width=True)

# # =====================================================
# # RUN-BY-RUN VIEW
# # =====================================================

# st.subheader("🔍 Detailed Outputs")

# for idx, r in enumerate(runs, start=1):

#     with st.expander(f"Run {idx} — {r['_file']}"):

#         col1, col2 = st.columns(2)

#         with col1:
#             st.markdown("### ⚙️ Metadata")
#             st.json({
#                 "model": r.get("model"),
#                 "prompt_file": r.get("prompt_file"),
#                 "pages": r.get("pages"),
#                 "temperature": r.get("temperature"),
#                 "max_tokens": r.get("max_tokens"),
#             })

#             st.markdown("### 🧠 Prompt")
#             st.text_area(
#                 "System Prompt",
#                 r.get("system_prompt", ""),
#                 height=220,
#                 key=f"prompt_{idx}"
#             )

#         with col2:
#             st.markdown("### 🤖 Model Output")

#             output_text = r.get("output", "")

#             # try parse JSON
#             try:
#                 parsed = json.loads(output_text)
#                 st.json(parsed)
#             except Exception:
#                 st.code(output_text)

# # =====================================================
# # OPTIONAL: ASPECT COMPARISON
# # =====================================================

# st.subheader("📈 Aspect Comparison (Quick View)")

# aspect_rows = []

# for r in runs:
#     try:
#         parsed = json.loads(r.get("output", "[]"))
#         for item in parsed:
#             aspect_rows.append({
#                 "file": r["_file"],
#                 "aspect": item.get("aspect"),
#                 "sentiment": item.get("sentiment"),
#                 "category": item.get("aspect_category"),
#             })
#     except Exception:
#         pass

# if aspect_rows:
#     df_aspect = pd.DataFrame(aspect_rows)
#     st.dataframe(df_aspect, use_container_width=True)
# else:
#     st.info("No structured JSON detected for aspect comparison.")
