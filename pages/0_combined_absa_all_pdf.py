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
st.title("🌍 Global Combined Aspect Table — All Experiment Sets")

st.markdown("""
This page aggregates **all ABSA outputs from all experiment sets**
into a unified **sentence × canonical aspect table**.
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


# =====================================================
# LOAD ASPECT MAPPING
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
# LOAD REGISTRY (ALL SETS)
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
# COLLECT ALL UNIQUE LOG FILES
# =====================================================

all_log_files = set()
file_to_sets = {}

for set_name, files in sets.items():
    for f in files:
        all_log_files.add(f)
        file_to_sets.setdefault(f, []).append(set_name)

st.sidebar.metric("Total Experiment Sets", len(sets))
st.sidebar.metric("Total Runs", len(all_log_files))

# =====================================================
# LOAD & NORMALIZE ALL RUNS
# =====================================================

rows = []

progress = st.progress(0.0)

for i, fname in enumerate(sorted(all_log_files), start=1):

    path = LOGS_DIR / fname
    if not path.exists():
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parsed = safe_json_load(data.get("output", ""))

    if not parsed:
        continue

    for it in parsed:
        if not isinstance(it, dict):
            continue

        sent = it.get("sentence")
        asp = it.get("aspect")

        if not sent or not asp:
            continue

        asp_norm = str(asp).lower().strip()
        asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

        rows.append({
            "run": fname,
            "experiment_sets": ", ".join(sorted(file_to_sets.get(fname, []))),

            "sentence": sent,
            "sentence_norm": " ".join(str(sent).split()),

            "aspect_raw": asp,
            "aspect_norm": asp_norm,
            "aspect_canonical": asp_map,

            "category": it.get("aspect_category"),
            "sentiment": it.get("sentiment"),
            "tone": it.get("tone"),
            "confidence": it.get("confidence"),
        })

    progress.progress(i / len(all_log_files))

if not rows:
    st.error("No ABSA data recovered from logs.")
    st.stop()

df = pd.DataFrame(rows)

# =====================================================
# GLOBAL COMBINED ASPECT TABLE
# =====================================================

st.subheader("📋 Global Combined Aspect Table")

combined = []

for (sent, asp), g in df.groupby(["sentence_norm", "aspect_canonical"]):

    combined.append({
        "sentence": sent,
        "canonical_aspect": asp,

        "runs_count": g["run"].nunique(),
        "runs": ", ".join(sorted(g["run"].unique())),

        "experiment_sets": ", ".join(sorted(
            set(", ".join(g["experiment_sets"]).split(", "))
        )),

        "raw_aspects": ", ".join(sorted(set(g["aspect_raw"].astype(str)))),

        "sentiments": ", ".join(sorted(set(g["sentiment"].astype(str)))),
        "tones": ", ".join(sorted(set(g["tone"].astype(str)))),

        "avg_confidence": pd.to_numeric(g["confidence"], errors="coerce").mean(),
    })

combined_df = pd.DataFrame(combined)

# =====================================================
# FILTERS
# =====================================================

st.sidebar.header("🔍 Filters")

aspect_filter = st.sidebar.multiselect(
    "Canonical Aspect",
    sorted(combined_df["canonical_aspect"].unique())
)

min_runs = st.sidebar.slider(
    "Minimum agreeing runs",
    1,
    combined_df["runs_count"].max(),
    2
)

view_df = combined_df.copy()

if aspect_filter:
    view_df = view_df[view_df["canonical_aspect"].isin(aspect_filter)]

view_df = view_df[view_df["runs_count"] >= min_runs]

st.caption(f"Showing {len(view_df)} of {len(combined_df)} entries")

st.dataframe(
    view_df.sort_values(["canonical_aspect", "runs_count"], ascending=[True, False]),
    use_container_width=True
)

# =====================================================
# PER-ASPECT STATS
# =====================================================

st.subheader("📊 Canonical Aspect Coverage (Global)")

stats = (
    combined_df
    .groupby("canonical_aspect")
    .agg(
        sentences=("sentence", "nunique"),
        total_occurrences=("runs_count", "sum"),
        avg_runs=("runs_count", "mean"),
    )
    .sort_values("sentences", ascending=False)
)

st.dataframe(stats, use_container_width=True)
st.bar_chart(stats["sentences"])

# =====================================================
# DOWNLOAD
# =====================================================

with st.expander("📥 Download"):

    st.download_button(
        "Download Combined Aspect Table (CSV)",
        view_df.to_csv(index=False).encode("utf-8"),
        "global_combined_aspect_table.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download Full Raw ABSA Rows (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        "global_absa_raw_rows.csv",
        mime="text/csv",
    )
