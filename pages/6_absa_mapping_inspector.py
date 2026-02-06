import streamlit as st
from pathlib import Path
import json
import pandas as pd
from collections import Counter, defaultdict

# =====================================================
# PATH SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"
LOGS_DIR = BASE_DIR / "logs"
REGISTRY_PATH = LOGS_DIR / "registry.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("🧭 Aspect Mapping Inspector & Ontology Builder")

# =====================================================
# LOAD MAPPING
# =====================================================

if not MAPPING_PATH.exists():
    st.error("❌ data/aspect_mapping.json not found.")
    st.stop()

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

groups = mapping_cfg.get("mappings", [])

rows = []
alias_set = set()

for g in groups:
    canonical = g["canonical"].lower().strip()
    aliases = [a.lower().strip() for a in g["aliases"]]
    alias_set.update(aliases)
    rows.append({
        "canonical": canonical,
        "aliases": ", ".join(sorted(aliases)),
        "alias_count": len(aliases),
    })

map_df = pd.DataFrame(rows)

# =====================================================
# MAPPING METRICS
# =====================================================

st.subheader("🧭 Mapping Coverage Overview")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Canonical Groups", len(groups))
with c2:
    st.metric("Total Aliases", len(alias_set))
with c3:
    st.metric("Avg Aliases / Group", round(map_df["alias_count"].mean(), 2) if not map_df.empty else 0)
with c4:
    st.metric("Max Aliases in Group", int(map_df["alias_count"].max()) if not map_df.empty else 0)

# =====================================================
# MAPPING GROUP TABLE
# =====================================================

st.subheader("📚 Mapping Groups")

if not map_df.empty:
    st.dataframe(map_df.sort_values("alias_count", ascending=False), use_container_width=True)
else:
    st.info("No mapping groups found.")

# =====================================================
# LOAD ASPECT LABELS FROM LOGS
# =====================================================

def safe_json_load(text):
    try:
        return json.loads(text)
    except Exception:
        return []


def normalize_items(items):
    out = []
    for it in items:
        if isinstance(it, dict):
            a = it.get("aspect")
            if a:
                out.append(a.lower().strip())
    return out


all_aspects = []
aspect_sets = defaultdict(set)

if REGISTRY_PATH.exists():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    for set_name, files in registry.get("sets", {}).items():
        for fname in files:
            path = LOGS_DIR / fname
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                parsed = safe_json_load(data.get("output", ""))
                labels = normalize_items(parsed)
                for a in labels:
                    all_aspects.append(a)
                    aspect_sets[a].add(set_name)

counter = Counter(all_aspects)
unique_aspects = set(counter.keys())
unmapped = sorted(unique_aspects - alias_set)

# =====================================================
# UNMAPPED ANALYSIS
# =====================================================

st.subheader("❗ Unmapped Aspect Labels from Experiments")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Unique Aspect Labels in Logs", len(unique_aspects))
with c2:
    st.metric("Mapped by Ontology", len(unique_aspects & alias_set))
with c3:
    st.metric("Unmapped Labels", len(unmapped))

unmapped_rows = [
    {
        "aspect_label": a,
        "frequency": counter[a],
        "experiment_sets": ", ".join(sorted(aspect_sets[a])),
    }
    for a in unmapped
]

if unmapped_rows:
    unmapped_df = pd.DataFrame(unmapped_rows)
    if "frequency" in unmapped_df.columns:
        unmapped_df = unmapped_df.sort_values("frequency", ascending=False)
else:
    unmapped_df = pd.DataFrame(columns=["aspect_label", "frequency", "experiment_sets"])

with st.expander("🔍 Unmapped Aspect Labels (Ranked by Frequency)"):
    st.dataframe(unmapped_df, use_container_width=True)

# =====================================================
# MAPPING BUILDER — ADD NEW GROUP
# =====================================================

st.subheader("🛠 Add New Mapping Group")

if unmapped:

    selected_aliases = st.multiselect(
        "Select unmapped labels to group",
        options=unmapped
    )

    canonical = st.text_input("Canonical Label (new or existing)")

    if st.button("➕ Add Mapping Group"):

        if not selected_aliases or not canonical.strip():
            st.warning("Select at least one alias and provide canonical label.")
        else:
            new_group = {
                "aliases": selected_aliases,
                "canonical": canonical.strip().lower()
            }

            mapping_cfg["mappings"].append(new_group)

            with open(MAPPING_PATH, "w", encoding="utf-8") as f:
                json.dump(mapping_cfg, f, indent=2, ensure_ascii=False)

            st.success("✅ Mapping group added and saved to aspect_mapping.json")
            st.info("Please refresh the page to reload updated mapping.")
else:
    st.success("🎉 No unmapped labels left — ontology fully covers dataset!")

# =====================================================
# EXPORT
# =====================================================

with st.expander("📥 Download Unmapped Labels"):
    st.download_button(
        "Download CSV",
        unmapped_df.to_csv(index=False).encode("utf-8"),
        "unmapped_aspect_labels.csv",
        mime="text/csv",
    )


# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd
# from collections import Counter, defaultdict

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"
# LOGS_DIR = BASE_DIR / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("🧭 Aspect Mapping Inspector & Coverage Analyzer")

# st.markdown("""
# This page visualizes **aspect ontology mappings** and shows which aspect labels
# from experiments are **not yet covered** by the mapping file.

# Source:
# - `data/aspect_mapping.json`
# - `logs/registry.json`
# """)

# # =====================================================
# # LOAD MAPPING
# # =====================================================

# if not MAPPING_PATH.exists():
#     st.error("❌ data/aspect_mapping.json not found.")
#     st.stop()

# with open(MAPPING_PATH, "r", encoding="utf-8") as f:
#     mapping_cfg = json.load(f)

# groups = mapping_cfg.get("mappings", [])

# rows = []
# alias_set = set()

# for g in groups:
#     canonical = g["canonical"].lower().strip()
#     aliases = [a.lower().strip() for a in g["aliases"]]
#     for a in aliases:
#         alias_set.add(a)
#     rows.append({
#         "canonical": canonical,
#         "aliases": ", ".join(sorted(aliases)),
#         "alias_count": len(aliases),
#     })

# map_df = pd.DataFrame(rows)

# # =====================================================
# # MAPPING METRICS
# # =====================================================

# st.subheader("🧭 Mapping Coverage Overview")

# c1, c2, c3, c4 = st.columns(4)

# with c1:
#     st.metric("Canonical Groups", len(groups))
# with c2:
#     st.metric("Total Aliases", len(alias_set))
# with c3:
#     st.metric("Avg Aliases / Group", round(map_df["alias_count"].mean(), 2))
# with c4:
#     st.metric("Max Aliases in Group", map_df["alias_count"].max())

# # =====================================================
# # MAPPING GROUP TABLE
# # =====================================================

# st.subheader("📚 Mapping Groups")

# st.dataframe(map_df.sort_values("alias_count", ascending=False), use_container_width=True)

# with st.expander("📥 Download Mapping Table"):
#     st.download_button(
#         "Download CSV",
#         map_df.to_csv(index=False).encode("utf-8"),
#         "aspect_mapping_groups.csv",
#         mime="text/csv",
#     )

# # =====================================================
# # LOAD ASPECT LABELS FROM LOGS
# # =====================================================

# def safe_json_load(text):
#     try:
#         return json.loads(text)
#     except Exception:
#         return []

# def normalize_items(items):
#     out = []
#     for it in items:
#         if isinstance(it, dict):
#             a = it.get("aspect")
#             if a:
#                 out.append(a.lower().strip())
#     return out


# all_aspects = []
# aspect_sets = defaultdict(set)

# if REGISTRY_PATH.exists():
#     with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#         registry = json.load(f)

#     for set_name, files in registry.get("sets", {}).items():
#         for fname in files:
#             path = LOGS_DIR / fname
#             if not path.exists():
#                 continue
#             with open(path, "r", encoding="utf-8") as f:
#                 data = json.load(f)
#                 parsed = safe_json_load(data.get("output", ""))
#                 labels = normalize_items(parsed)
#                 for a in labels:
#                     all_aspects.append(a)
#                     aspect_sets[a].add(set_name)

# counter = Counter(all_aspects)
# unique_aspects = set(counter.keys())

# unmapped = sorted(unique_aspects - alias_set)

# # =====================================================
# # UNMAPPED ANALYSIS
# # =====================================================

# st.subheader("❗ Unmapped Aspect Labels from Experiments")

# c1, c2, c3 = st.columns(3)

# with c1:
#     st.metric("Unique Aspect Labels in Logs", len(unique_aspects))
# with c2:
#     st.metric("Mapped by Ontology", len(unique_aspects & alias_set))
# with c3:
#     st.metric("Unmapped Labels", len(unmapped))

# unmapped_rows = []

# for a in unmapped:
#     unmapped_rows.append({
#         "aspect_label": a,
#         "frequency": counter[a],
#         "experiment_sets": ", ".join(sorted(aspect_sets[a])),
#     })

# unmapped_df = pd.DataFrame(unmapped_rows).sort_values("frequency", ascending=False)

# with st.expander("🔍 Unmapped Aspect Labels (Ranked by Frequency)"):
#     st.dataframe(unmapped_df, use_container_width=True)

# with st.expander("📥 Download Unmapped Labels"):
#     st.download_button(
#         "Download CSV",
#         unmapped_df.to_csv(index=False).encode("utf-8"),
#         "unmapped_aspect_labels.csv",
#         mime="text/csv",
#     )

# # =====================================================
# # SUGGEST GROUPING AID (MANUAL)
# # =====================================================

# st.subheader("🛠 Manual Mapping Helper")

# st.markdown("""
# Use this section to **inspect similar labels manually** before adding them
# to `data/aspect_mapping.json`.
# """)

# search = st.text_input("Search unmapped labels")

# if search:
#     matches = unmapped_df[unmapped_df["aspect_label"].str.contains(search.lower())]
#     st.dataframe(matches, use_container_width=True)
