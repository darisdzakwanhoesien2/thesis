import streamlit as st
from pathlib import Path
import json
import pandas as pd

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
REGISTRY_PATH = BASE_DIR / "logs" / "registry.json"
COMPANY_DIR = BASE_DIR / "data" / "company_json"
MASTER_PATH = COMPANY_DIR / "company_master.json"
OUT_PATH = COMPANY_DIR / "company_registry.json"

COMPANY_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="🏢 Company ↔ Experiment Mapping", layout="wide")
st.title("🏢 Company Mapping from Registry Sets")

# =====================================================
# LOAD FILES
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ logs/registry.json not found.")
    st.stop()

if not MASTER_PATH.exists():
    st.error("❌ data/company_json/company_master.json not found.")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

with open(MASTER_PATH, "r", encoding="utf-8") as f:
    companies = json.load(f)

sets = registry.get("sets", {})

# =====================================================
# INIT COMPANY MAP (ADD UNDEFINED)
# =====================================================

company_map = {c["ticker"]: {**c, "sets": []} for c in companies}

company_map["UNDEFINED"] = {
    "ticker": "UNDEFINED",
    "name": "Unassigned / To Be Decided",
    "full": "Unassigned Experiment Sets",
    "aliases": [],
    "sets": [],
}

unmatched_sets = []

# =====================================================
# MATCH SETS TO COMPANIES
# =====================================================

for set_name, files in sets.items():
    matched = False
    lname = set_name.lower()

    for c in companies:
        for alias in c.get("aliases", []):
            if alias and alias.lower() in lname:
                company_map[c["ticker"]]["sets"].append({
                    "set_name": set_name,
                    "runs": len(files),
                    "files": files,
                })
                matched = True
                break
        if matched:
            break

    if not matched:
        unmatched_sets.append(set_name)
        company_map["UNDEFINED"]["sets"].append({
            "set_name": set_name,
            "runs": len(files),
            "files": files,
        })

# =====================================================
# SAVE OUTPUT
# =====================================================

if st.button("💾 Build company_registry.json"):
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(company_map, f, indent=2)
    st.success(f"Saved to {OUT_PATH}")

# =====================================================
# TABLE VIEW
# =====================================================

rows = []

for tkr, c in company_map.items():
    total_runs = sum(s["runs"] for s in c["sets"])
    rows.append({
        "Ticker": tkr,
        "Company": c["name"],
        "Matched Sets": len(c["sets"]),
        "Total Runs": total_runs,
    })

df = pd.DataFrame(rows).sort_values("Total Runs", ascending=False)

st.subheader("📊 Company Coverage Overview (Including UNDEFINED)")
st.dataframe(df, use_container_width=True)

# =====================================================
# DETAIL VIEW
# =====================================================

st.divider()
st.subheader("🔍 Company Details")

selected = st.selectbox("Select company", df["Ticker"])

company = company_map[selected]

st.markdown(f"### {company['full']} ({company['ticker']})")

if company["sets"]:
    for s in company["sets"]:
        st.markdown(f"**{s['set_name']}** — {s['runs']} runs")
        with st.expander("Files"):
            for f in s["files"]:
                st.text(f)
else:
    st.info("No experiment sets assigned.")

# =====================================================
# UNMATCHED SETS (AUDIT VIEW)
# =====================================================

st.divider()
st.subheader("⚠ Unmatched Sets (Also Stored Under UNDEFINED)")

if unmatched_sets:
    st.warning(f"{len(unmatched_sets)} sets not mapped to any company.")
    for s in unmatched_sets:
        st.text(s)
else:
    st.success("All sets mapped successfully.")
