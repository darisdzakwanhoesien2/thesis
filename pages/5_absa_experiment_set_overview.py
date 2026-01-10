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
MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📊 ABSA Experiment Set Overview — Mapping & Agreement Comparison")

st.markdown("""
This page summarizes **entity mapping coverage and agreement improvement**
across **all experiment sets**.

Each row = one experiment set.
""")

# =====================================================
# UTIL — ROBUST JSON RECOVERY
# =====================================================

def recover_json_objects(text):
    objects, buf, depth, in_obj = [], "", 0, False
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
                buf, in_obj = "", False
    return objects


def extract_json_arrays(text):
    arrays, stack, start = [], [], None
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
    for arr in reversed(extract_json_arrays(text)):
        try:
            return json.loads(arr)
        except Exception:
            continue
    return recover_json_objects(text)


def normalize_items(items):
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rows.append({
            "sentence": it.get("sentence"),
            "aspect": it.get("aspect"),
        })
    return rows


def agreement(values):
    v = [str(x).strip().lower() for x in values if pd.notna(x)]
    if not v:
        return "N/A"
    return "AGREE" if len(set(v)) == 1 else "DISAGREE"


# =====================================================
# LOAD ASPECT MAPPING (ALIAS GROUPS)
# =====================================================

if not MAPPING_PATH.exists():
    st.error("❌ data/aspect_mapping.json not found.")
    st.stop()

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

ASPECT_MAP = {}
for group in mapping_cfg.get("mappings", []):
    canonical = group["canonical"].lower().strip()
    for alias in group["aliases"]:
        ASPECT_MAP[alias.lower().strip()] = canonical

# =====================================================
# LOAD REGISTRY
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ registry.json not found.")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

sets = registry.get("sets", {})
if not sets:
    st.error("❌ No experiment sets found.")
    st.stop()

# =====================================================
# PROCESS EACH EXPERIMENT SET
# =====================================================

summary_rows = []

progress = st.progress(0.0)
status = st.empty()

for i, (set_name, log_files) in enumerate(sets.items(), start=1):

    status.info(f"Processing: {set_name}")

    rows = []

    for fname in log_files:
        path = LOGS_DIR / fname
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            parsed = safe_json_load(data.get("output", ""))
            if parsed:
                rows.extend(normalize_items(parsed))

    if not rows:
        continue

    df = pd.DataFrame(rows)

    df["sentence_norm"] = df["sentence"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["aspect_norm"] = df["aspect"].astype(str).str.lower().str.strip()
    df["aspect_mapped"] = df["aspect_norm"].map(ASPECT_MAP).fillna(df["aspect_norm"])

    # -------- Mapping Coverage --------
    unique_aspects = df["aspect_norm"].nunique()
    mapped_labels = len(set(df["aspect_norm"]) & set(ASPECT_MAP.keys()))
    unmapped_labels = unique_aspects - mapped_labels

    # -------- Agreement Before / After --------
    before_bad = 0
    after_bad = 0
    fixed = 0

    for _, g in df.groupby("sentence_norm"):
        raw = g["aspect_norm"].tolist()
        mapped = g["aspect_mapped"].tolist()

        b = agreement(raw)
        a = agreement(mapped)

        if b == "DISAGREE":
            before_bad += 1
        if a == "DISAGREE":
            after_bad += 1
        if b == "DISAGREE" and a == "AGREE":
            fixed += 1

    summary_rows.append({
        "experiment_set": set_name,
        "runs": len(log_files),

        # Mapping coverage
        "unique_aspect_labels": unique_aspects,
        "mapped_labels": mapped_labels,
        "unmapped_labels": unmapped_labels,

        # Agreement improvement
        "disagree_before": before_bad,
        "disagree_after": after_bad,
        "fixed_by_mapping": fixed,
        "total_sentences": df["sentence_norm"].nunique(),
    })

    progress.progress(i / len(sets))

status.success("✅ All experiment sets processed")

summary_df = pd.DataFrame(summary_rows)

# =====================================================
# TABLE VIEW
# =====================================================

st.subheader("📋 Experiment Set Comparison Table")

st.dataframe(summary_df, use_container_width=True)

# =====================================================
# SORT & RANKING
# =====================================================

st.subheader("🏆 Ranking by Mapping Benefit")

rank_df = summary_df.copy()
rank_df["fix_ratio"] = rank_df["fixed_by_mapping"] / rank_df["disagree_before"].replace(0, 1)

st.dataframe(
    rank_df.sort_values("fix_ratio", ascending=False),
    use_container_width=True
)

# =====================================================
# CHARTS
# =====================================================

st.subheader("📊 Comparison Charts")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### ❌ Disagreement Before vs After")
    chart_df = summary_df.set_index("experiment_set")[["disagree_before", "disagree_after"]]
    st.bar_chart(chart_df)

with c2:
    st.markdown("### 🛠 Fixed by Mapping")
    chart_df = summary_df.set_index("experiment_set")[["fixed_by_mapping"]]
    st.bar_chart(chart_df)

# =====================================================
# DOWNLOAD
# =====================================================

with st.expander("📥 Download Summary"):
    st.download_button(
        "Download CSV",
        summary_df.to_csv(index=False).encode("utf-8"),
        "experiment_set_mapping_summary.csv",
        mime="text/csv",
    )
