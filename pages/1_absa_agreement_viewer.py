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
st.title("🧬 ABSA Agreement & Disagreement Analyzer")

# =====================================================
# UTIL — ROBUST JSON RECOVERY
# =====================================================

def recover_json_objects(text):
    objects = []
    buf = ""
    depth = 0
    in_obj = False

    for ch in text:
        if ch == "{":
            depth += 1
            in_obj = True
        if in_obj:
            buf += ch
        if ch == "}":
            depth -= 1
            if depth == 0 and buf:
                try:
                    objects.append(json.loads(buf))
                except Exception:
                    pass
                buf = ""
                in_obj = False
    return objects


def extract_json_arrays(text):
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
    arrays = extract_json_arrays(text)
    for arr in reversed(arrays):
        try:
            return json.loads(arr)
        except Exception:
            continue
    return recover_json_objects(text)


def normalize_items(items, file):
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue

        rows.append({
            "file": file,
            "sentence": it.get("sentence"),
            "aspect": it.get("aspect"),
            "category": it.get("aspect_category"),
            "sentiment": it.get("sentiment"),
            "tone": it.get("tone"),
            "confidence": it.get("confidence"),
        })
    return rows


# =====================================================
# AGREEMENT LOGIC
# =====================================================

def agreement(values):
    v = [str(x).strip().lower() for x in values if pd.notna(x)]
    if not v:
        return "N/A"
    return "AGREE" if len(set(v)) == 1 else "DISAGREE"


def overall_agreement(a, b, c, d):
    flags = [a, b, c, d]
    if all(x == "AGREE" for x in flags):
        return "FULL_AGREE"
    if all(x == "DISAGREE" for x in flags):
        return "FULL_DISAGREE"
    return "PARTIAL"


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
# LOAD LOG FILES
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
# RUN SUMMARY
# =====================================================

st.subheader("📋 Run Summary")

summary = [{
    "file": r["_file"],
    "model": r.get("model"),
    "prompt": r.get("prompt_file"),
    "pages": len(r.get("pages", [])),
    "temperature": r.get("temperature"),
    "max_tokens": r.get("max_tokens"),
} for r in runs]

st.dataframe(pd.DataFrame(summary), use_container_width=True)

# =====================================================
# PARSE ALL ABSA OUTPUTS
# =====================================================

all_rows = []

for r in runs:
    parsed = safe_json_load(r.get("output", ""))
    if parsed:
        all_rows.extend(normalize_items(parsed, r["_file"]))

if not all_rows:
    st.error("No structured ABSA items recovered.")
    st.stop()

df = pd.DataFrame(all_rows)

# =====================================================
# NORMALIZATION
# =====================================================

df["sentence_norm"] = df["sentence"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
df["aspect_norm"] = df["aspect"].astype(str).str.lower().str.strip()
df["category_norm"] = df["category"].astype(str).str.upper().str.strip()
df["sentiment_norm"] = df["sentiment"].astype(str).str.lower().str.strip()
df["tone_norm"] = df["tone"].astype(str).str.lower().str.strip()

# =====================================================
# AGREEMENT ANALYSIS
# =====================================================

rows = []

for s, g in df.groupby("sentence_norm"):

    aspects = g["aspect_norm"].tolist()
    cats = g["category_norm"].tolist()
    sents = g["sentiment_norm"].tolist()
    roles = g["tone_norm"].tolist()

    a_ag = agreement(aspects)
    c_ag = agreement(cats)
    s_ag = agreement(sents)
    r_ag = agreement(roles)

    rows.append({
        "sentence": s,
        "runs": len(g),
        "aspect_labels": " | ".join(sorted(set(aspects))),
        "esg_labels": " | ".join(sorted(set(cats))),
        "sentiments": " | ".join(sorted(set(sents))),
        "roles": " | ".join(sorted(set(roles))),
        "aspect_agreement": a_ag,
        "esg_agreement": c_ag,
        "sentiment_agreement": s_ag,
        "role_agreement": r_ag,
        "overall": overall_agreement(a_ag, c_ag, s_ag, r_ag),
    })

agree_df = pd.DataFrame(rows)

# =====================================================
# METRICS
# =====================================================

st.subheader("📊 Agreement Overview")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("FULL AGREE", (agree_df["overall"] == "FULL_AGREE").sum())
with c2:
    st.metric("PARTIAL", (agree_df["overall"] == "PARTIAL").sum())
with c3:
    st.metric("FULL DISAGREE", (agree_df["overall"] == "FULL_DISAGREE").sum())
with c4:
    st.metric("Aspect Disagree", (agree_df["aspect_agreement"] == "DISAGREE").sum())
with c5:
    st.metric("Sentiment Disagree", (agree_df["sentiment_agreement"] == "DISAGREE").sum())

# =====================================================
# FILTER + VIEW
# =====================================================

st.subheader("🔍 Sentence-Level Agreement Table")

filt = st.multiselect(
    "Show sentences with:",
    ["FULL_AGREE", "PARTIAL", "FULL_DISAGREE"],
    default=["PARTIAL", "FULL_DISAGREE"],
)

view_df = agree_df[agree_df["overall"].isin(filt)]

st.dataframe(view_df, use_container_width=True)

# =====================================================
# EXPORT
# =====================================================

with st.expander("📥 Download Results"):
    st.download_button(
        "Download Agreement CSV",
        agree_df.to_csv(index=False).encode("utf-8"),
        "sentence_agreement_analysis.csv",
        mime="text/csv",
    )
