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
st.title("🧠 ABSA Entity Mapping — Agreement Before & After Normalization")

st.markdown("""
This page analyzes **aspect label disagreement** across ABSA runs and shows how much
disagreement is caused by **label variation** rather than semantic errors, using
a manually defined **alias → canonical mapping**.
""")

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


# =====================================================
# LOAD ASPECT MAPPING (ALIAS GROUPS)
# =====================================================

if not MAPPING_PATH.exists():
    st.error("❌ data/aspect_mapping.json not found.")
    st.stop()

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

ASPECT_MAP = {}
GROUPS = []

for group in mapping_cfg.get("mappings", []):
    canonical = group["canonical"].lower().strip()
    GROUPS.append(canonical)
    for alias in group["aliases"]:
        ASPECT_MAP[alias.lower().strip()] = canonical

st.sidebar.subheader("🧭 Mapping Groups (Preview)")
st.sidebar.json(mapping_cfg["mappings"][:5])

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
    st.error("❌ No experiment sets found.")
    st.stop()

# =====================================================
# SELECT SET
# =====================================================

st.sidebar.header("🧪 Experiment Set")

selected_set = st.sidebar.selectbox("Select Result Set", set_names)
log_files = registry["sets"][selected_set]
st.sidebar.success(f"{len(log_files)} runs")

# =====================================================
# LOAD LOGS
# =====================================================

rows = []

for fname in log_files:
    path = LOGS_DIR / fname
    if not path.exists():
        continue
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        parsed = safe_json_load(data.get("output", ""))
        if parsed:
            rows.extend(normalize_items(parsed, fname))

if not rows:
    st.error("No ABSA data found.")
    st.stop()

df = pd.DataFrame(rows)

# =====================================================
# NORMALIZATION
# =====================================================

df["sentence_norm"] = df["sentence"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
df["aspect_norm"] = df["aspect"].astype(str).str.lower().str.strip()

df["aspect_mapped"] = df["aspect_norm"].map(ASPECT_MAP).fillna(df["aspect_norm"])

# =====================================================
# MAPPING COVERAGE
# =====================================================

st.subheader("🧭 Mapping Coverage")

unmapped = sorted(set(df["aspect_norm"]) - set(ASPECT_MAP.keys()))

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Unique Aspect Labels", df["aspect_norm"].nunique())
with c2:
    st.metric("Mapped Labels", len(set(ASPECT_MAP.keys())))
with c3:
    st.metric("Unmapped Labels", len(unmapped))

with st.expander("🔍 Unmapped Aspect Labels"):
    st.write(unmapped)

# =====================================================
# AGREEMENT BEFORE & AFTER
# =====================================================

records = []

for s, g in df.groupby("sentence_norm"):

    raw_aspects = g["aspect_norm"].tolist()
    mapped_aspects = g["aspect_mapped"].tolist()

    before = agreement(raw_aspects)
    after = agreement(mapped_aspects)

    records.append({
        "sentence": s,
        "raw_labels": " | ".join(sorted(set(raw_aspects))),
        "mapped_labels": " | ".join(sorted(set(mapped_aspects))),
        "before_mapping": before,
        "after_mapping": after,
    })

cmp_df = pd.DataFrame(records)

# =====================================================
# METRICS
# =====================================================

st.subheader("📊 Agreement Improvement via Entity Mapping")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("❌ Disagree Before", (cmp_df["before_mapping"] == "DISAGREE").sum())
with c2:
    st.metric("❌ Disagree After", (cmp_df["after_mapping"] == "DISAGREE").sum())
with c3:
    fixed = ((cmp_df["before_mapping"] == "DISAGREE") & (cmp_df["after_mapping"] == "AGREE")).sum()
    st.metric("🛠 Fixed by Mapping", fixed)
with c4:
    st.metric("Total Sentences", len(cmp_df))

# =====================================================
# DISTRIBUTION
# =====================================================

st.subheader("📊 Distribution Before vs After Mapping")

dist_df = pd.DataFrame({
    "Before": cmp_df["before_mapping"].value_counts(),
    "After": cmp_df["after_mapping"].value_counts(),
}).fillna(0)

st.bar_chart(dist_df)

# =====================================================
# DISAGREEMENT TABLES
# =====================================================

st.subheader("📋 Sentence-Level Comparison")

before_bad = cmp_df[cmp_df["before_mapping"] == "DISAGREE"]
fixed_df = cmp_df[
    (cmp_df["before_mapping"] == "DISAGREE") &
    (cmp_df["after_mapping"] == "AGREE")
]
still_bad = cmp_df[
    (cmp_df["before_mapping"] == "DISAGREE") &
    (cmp_df["after_mapping"] == "DISAGREE")
]

with st.expander(f"❌ Disagreement BEFORE Mapping — {len(before_bad)} sentences"):
    st.dataframe(before_bad, use_container_width=True)

with st.expander(f"✅ Fixed by Mapping — {len(fixed_df)} sentences"):
    st.dataframe(fixed_df, use_container_width=True)

with st.expander(f"❗ Still Disagree After Mapping — {len(still_bad)} sentences"):
    st.dataframe(still_bad, use_container_width=True)

# =====================================================
# DOWNLOAD
# =====================================================

with st.expander("📥 Download Mapping Analysis"):
    st.download_button(
        "Download CSV",
        cmp_df.to_csv(index=False).encode("utf-8"),
        "aspect_mapping_comparison.csv",
        mime="text/csv",
    )
