import streamlit as st
from pathlib import Path
import json
import pandas as pd

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
# PATH DISCOVERY (DEPLOYMENT SAFE)
# =====================================================

def find_repo_root(start: Path) -> Path:
    """
    Walk upward until we find a directory containing 'logs/' or 'data/'.
    Works reliably across Streamlit Cloud, Docker, and local runs.
    """
    start = start.resolve()

    for parent in [start] + list(start.parents):
        if (parent / "logs").exists() or (parent / "data").exists():
            return parent

    return start


PROJECT_ROOT = find_repo_root(Path.cwd())
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = LOGS_DIR / "registry.json"
MAPPING_PATH = DATA_DIR / "aspect_mapping.json"

# =====================================================
# DIAGNOSTICS (VISIBLE IN SIDEBAR)
# =====================================================

with st.sidebar.expander("🧪 Path Diagnostics"):
    st.write("cwd:", Path.cwd())
    st.write("Resolved project root:", PROJECT_ROOT)
    st.write("Logs dir:", LOGS_DIR)
    st.write("Registry path:", REGISTRY_PATH)
    st.write("Registry exists:", REGISTRY_PATH.exists())
    st.write("Mapping path:", MAPPING_PATH)
    st.write("Mapping exists:", MAPPING_PATH.exists())
    st.write("Root contents:", [p.name for p in PROJECT_ROOT.iterdir()])
    st.write("Log files:", sorted([p.name for p in LOGS_DIR.glob("*.json")]))

# =====================================================
# ENSURE REGISTRY EXISTS (NON-DESTRUCTIVE)
# =====================================================

if not REGISTRY_PATH.exists():
    REGISTRY_PATH.write_text(json.dumps({
        "created_at": None,
        "sets": {}
    }, indent=2))

# =====================================================
# SAFE JSON HELPERS
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
    st.error(f"❌ Missing aspect_mapping.json at {MAPPING_PATH}")
    st.stop()

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

ASPECT_MAP = {}
for group in mapping_cfg.get("mappings", []):
    canonical = group["canonical"].lower().strip()
    for alias in group["aliases"]:
        ASPECT_MAP[alias.lower().strip()] = canonical

# =====================================================
# LOAD REGISTRY (AUTO-RECOVERY ENABLED)
# =====================================================

try:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
except Exception:
    registry = {"created_at": None, "sets": {}}

sets = registry.get("sets", {})

# -----------------------------------------------------
# AUTO DISCOVERY WHEN REGISTRY EMPTY (CLOUD SAFE)
# -----------------------------------------------------

if not sets:
    st.warning("⚠️ Registry empty — attempting auto-discovery from logs folder.")

    discovered = sorted(LOGS_DIR.glob("*.json"))
    discovered = [p.name for p in discovered if p.name != "registry.json"]

    if discovered:
        sets = {"auto_discovered": discovered}
        registry["sets"] = sets

        # Persist recovered registry
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2))

        st.success(f"✅ Auto-registered {len(discovered)} log files.")
    else:
        st.warning("⚠️ No log files found in logs/.")

# =====================================================
# COLLECT LOG FILES
# =====================================================

all_log_files = set()
file_to_sets = {}

for set_name, files in sets.items():
    for f in files:
        all_log_files.add(f)
        file_to_sets.setdefault(f, []).append(set_name)

st.sidebar.metric("Experiment Sets", len(sets))
st.sidebar.metric("Total Runs", len(all_log_files))

# =====================================================
# LOAD & NORMALIZE LOGS
# =====================================================

rows = []

if all_log_files:

    progress = st.progress(0.0)

    for i, fname in enumerate(sorted(all_log_files), start=1):

        path = LOGS_DIR / fname
        if not path.exists():
            st.warning(f"⚠️ Missing log file: {fname}")
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            st.warning(f"⚠️ Failed to load {fname}: {e}")
            continue

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

# =====================================================
# HANDLE EMPTY DATA
# =====================================================

if not rows:
    st.info("ℹ️ No ABSA data available yet.")
    st.stop()

df = pd.DataFrame(rows)

# =====================================================
# GLOBAL COMBINED TABLE
# =====================================================

st.subheader("📋 Global Combined Aspect Table")

combined = []

for (sent, asp), g in df.groupby(["sentence_norm", "aspect_canonical"]):

    cats = g["category"].dropna().astype(str).tolist()
    majority_cat = pd.Series(cats).mode().iloc[0] if cats else None

    combined.append({
        "sentence": sent,
        "canonical_aspect": asp,

        "runs_count": g["run"].nunique(),
        "runs": ", ".join(sorted(g["run"].unique())),
        "experiment_sets": ", ".join(sorted(
            set(", ".join(g["experiment_sets"]).split(", "))
        )),

        "raw_aspects": ", ".join(sorted(set(g["aspect_raw"].astype(str)))),
        "aspect_categories": ", ".join(sorted(set(cats))),
        "majority_category": majority_cat,

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
    int(combined_df["runs_count"].max()),
    1
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

st.subheader("📊 Canonical Aspect Coverage")

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
        "Download Combined Table (CSV)",
        view_df.to_csv(index=False).encode("utf-8"),
        "global_combined_aspect_table.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download Raw Rows (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        "global_absa_raw_rows.csv",
        mime="text/csv",
    )
