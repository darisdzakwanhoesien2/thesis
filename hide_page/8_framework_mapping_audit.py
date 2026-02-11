import json
import streamlit as st
import pandas as pd

st.header("🧭 Research Framework Mapping Audit")

# -------------------------------------------------
# Load framework
# -------------------------------------------------
with open("data/research_framework.json") as f:
    fw = json.load(f)

# -------------------------------------------------
# Helper
# -------------------------------------------------
def to_df(items, section):
    rows = []
    for it in items:
        rows.append({
            "id": it.get("id", it),
            "label": it.get("label") or it.get("title") or it.get("text") or it.get("name") or it
        })
    return pd.DataFrame(rows)

# -------------------------------------------------
# Normalize Metrics
# -------------------------------------------------
metrics_items = []
if isinstance(fw.get("metrics"), dict):
    for _, lst in fw["metrics"].items():
        for m in lst:
            metrics_items.append({"id": m, "label": m})
else:
    metrics_items = fw.get("metrics", [])

# -------------------------------------------------
# SECTION 1 — ENTITY INVENTORY
# -------------------------------------------------

st.subheader("📦 Framework Components")

with st.expander("Research Questions"):
    st.dataframe(to_df(fw["research_questions"], "RQ"), use_container_width=True)

with st.expander("Objectives"):
    st.dataframe(to_df(fw["objectives"], "O"), use_container_width=True)

with st.expander("Methodology"):
    st.dataframe(to_df(fw["methodology"], "M"), use_container_width=True)

with st.expander("Hypotheses"):
    st.dataframe(to_df(fw["hypotheses"], "H"), use_container_width=True)

with st.expander("Metrics"):
    st.dataframe(to_df(metrics_items, "Metric"), use_container_width=True)

# -------------------------------------------------
# SECTION 2 — CONNECTION TABLE
# -------------------------------------------------

st.subheader("🔗 Declared Mappings")

links_df = pd.DataFrame(fw["connections"])
st.dataframe(links_df, use_container_width=True)

# -------------------------------------------------
# SECTION 3 — UNMAPPED ANALYSIS
# -------------------------------------------------

st.subheader("⚠️ Unmapped Components")

all_sources = set(l["source"] for l in fw["connections"])
all_targets = set(l["target"] for l in fw["connections"])

def find_unmapped(items, direction="source"):
    ids = set(i["id"] for i in items)
    if direction == "source":
        return sorted(ids - all_sources)
    else:
        return sorted(ids - all_targets)

rq_unmapped = find_unmapped(fw["research_questions"], "source")
obj_unmapped = find_unmapped(fw["objectives"], "source")
meth_unmapped = find_unmapped(fw["methodology"], "source")
hyp_unmapped = find_unmapped(fw["hypotheses"], "target")
metric_unmapped = sorted(set(m["id"] for m in metrics_items) - all_targets)

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔍 Not Linked as Source")
    st.write("RQ:", rq_unmapped)
    st.write("Objectives:", obj_unmapped)
    st.write("Methods:", meth_unmapped)

with col2:
    st.markdown("### 🎯 Not Linked as Target")
    st.write("Hypotheses:", hyp_unmapped)
    st.write("Metrics:", metric_unmapped)

# -------------------------------------------------
# SECTION 4 — COVERAGE SUMMARY
# -------------------------------------------------

st.subheader("📊 Mapping Coverage Summary")

def coverage(total, unmapped):
    return round(100 * (1 - len(unmapped)/max(total,1)), 1)

summary = pd.DataFrame([
    {"Component": "Research Questions", "Coverage %": coverage(len(fw["research_questions"]), rq_unmapped)},
    {"Component": "Objectives", "Coverage %": coverage(len(fw["objectives"]), obj_unmapped)},
    {"Component": "Methodology", "Coverage %": coverage(len(fw["methodology"]), meth_unmapped)},
    {"Component": "Hypotheses", "Coverage %": coverage(len(fw["hypotheses"]), hyp_unmapped)},
    {"Component": "Metrics", "Coverage %": coverage(len(metrics_items), metric_unmapped)},
])

st.dataframe(summary, use_container_width=True)

st.info("Unmapped elements indicate research gaps or design extensions (e.g., RQ4 → Decision Support actions).")
