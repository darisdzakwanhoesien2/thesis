import streamlit as st
from pathlib import Path
import json
import pandas as pd
from collections import Counter, defaultdict
import matplotlib.pyplot as plt

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]

REGISTRY_PATH = BASE_DIR / "logs" / "registry.json"
COMPANY_REG_PATH = BASE_DIR / "data" / "company_json" / "company_registry.json"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="📊 Company ESG-ABSA Dashboard", layout="wide")
st.title("📊 Company × ESG × Sentiment — ABSA Analytics Dashboard")

# =====================================================
# LOAD REGISTRY
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ logs/registry.json not found")
    st.stop()

if not COMPANY_REG_PATH.exists():
    st.error("❌ data/company_json/company_registry.json not found")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

with open(COMPANY_REG_PATH, "r", encoding="utf-8") as f:
    company_registry = json.load(f)

sets = registry.get("sets", {})

# =====================================================
# ABSA OUTPUT ROOT SELECTION
# =====================================================

st.sidebar.header("📁 ABSA Output Location")

default_dirs = [
    BASE_DIR / "outputs_absa",
    BASE_DIR / "logs",
    BASE_DIR / "outputs",
]

existing_dirs = [p for p in default_dirs if p.exists()]

if not existing_dirs:
    st.error("❌ No ABSA output folders found. Add outputs_absa/ or logs/")
    st.stop()

absa_root = st.sidebar.selectbox(
    "Select ABSA results folder",
    existing_dirs,
    format_func=lambda p: str(p.relative_to(BASE_DIR)),
)

# =====================================================
# UTIL
# =====================================================

def load_absa_file(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def extract_fields(rec):
    aspect_cat = rec.get("aspect_categories") or rec.get("aspect_category")
    sentiment = rec.get("sentiments") or rec.get("sentiment")
    tone = rec.get("tones") or rec.get("tone")
    return aspect_cat, sentiment, tone


def prompt_from_name(fname):
    if "zero" in fname:
        return "zero_shot"
    if "few" in fname:
        return "few_shot"
    if "cot" in fname:
        return "cot"
    return "unknown"

# =====================================================
# COLLECT COMPANY DATA
# =====================================================

company_stats = {}

for ticker, comp in company_registry.items():

    rows = []
    file_paths = []

    for s in comp.get("sets", []):
        for fname in s.get("files", []):
            p = absa_root / fname
            if p.exists():
                file_paths.append(p)

    aspect_counter = Counter()
    sentiment_counter = Counter()
    tone_counter = Counter()
    prompt_counter = Counter()

    for p in file_paths:
        records = load_absa_file(p)
        prompt = prompt_from_name(p.name)

        for r in records:
            a, s, t = extract_fields(r)
            if a:
                aspect_counter[a] += 1
            if s:
                sentiment_counter[s] += 1
            if t:
                tone_counter[t] += 1
            prompt_counter[prompt] += 1

    company_stats[ticker] = {
        "company": comp.get("company", ticker),
        "aspects": aspect_counter,
        "sentiments": sentiment_counter,
        "tones": tone_counter,
        "prompts": prompt_counter,
        "files": len(file_paths),
    }

# =====================================================
# SUMMARY TABLE
# =====================================================

summary_rows = []

for t, d in company_stats.items():
    summary_rows.append({
        "Ticker": t,
        "Company": d["company"],
        "ABSA Files": d["files"],
        "Aspect Mentions": sum(d["aspects"].values()),
        "Sentiment Mentions": sum(d["sentiments"].values()),
    })

summary_df = pd.DataFrame(summary_rows).sort_values("Aspect Mentions", ascending=False)

st.subheader("🏢 Company Summary")
st.dataframe(summary_df, use_container_width=True)

# =====================================================
# COMPANY DETAIL VIEW
# =====================================================

st.divider()
st.subheader("🔍 Company Detail Analysis")

selected = st.selectbox("Select company", summary_df["Ticker"])

data = company_stats[selected]

st.markdown(f"### {data['company']} ({selected})")

col1, col2, col3 = st.columns(3)

# -------- ASPECTS --------
with col1:
    st.markdown("#### 🌍 ESG Aspect Categories")
    if data["aspects"]:
        fig = plt.figure()
        pd.Series(data["aspects"]).plot(kind="bar")
        st.pyplot(fig)
        st.dataframe(pd.Series(data["aspects"]).rename("count").reset_index())
    else:
        st.info("No aspect data.")

# -------- SENTIMENTS --------
with col2:
    st.markdown("#### 😊 Sentiments")
    if data["sentiments"]:
        fig = plt.figure()
        pd.Series(data["sentiments"]).plot(kind="bar")
        st.pyplot(fig)
        st.dataframe(pd.Series(data["sentiments"]).rename("count").reset_index())
    else:
        st.info("No sentiment data.")

# -------- TONES --------
with col3:
    st.markdown("#### 🎯 Tones")
    if data["tones"]:
        fig = plt.figure()
        pd.Series(data["tones"]).plot(kind="bar")
        st.pyplot(fig)
        st.dataframe(pd.Series(data["tones"]).rename("count").reset_index())
    else:
        st.info("No tone data.")

# =====================================================
# PROMPT STRATEGY COMPARISON
# =====================================================

st.divider()
st.subheader("🧪 Prompt Strategy Distribution")

if data["prompts"]:
    fig = plt.figure()
    pd.Series(data["prompts"]).plot(kind="bar")
    st.pyplot(fig)
    st.dataframe(pd.Series(data["prompts"]).rename("count").reset_index())
else:
    st.info("No prompt info detected.")

# =====================================================
# EXPORT
# =====================================================

st.divider()
st.subheader("⬇ Export Company Statistics")

export_rows = []

for t, d in company_stats.items():
    for k, v in d["aspects"].items():
        export_rows.append({
            "ticker": t,
            "company": d["company"],
            "metric": "aspect",
            "label": k,
            "count": v,
        })
    for k, v in d["sentiments"].items():
        export_rows.append({
            "ticker": t,
            "company": d["company"],
            "metric": "sentiment",
            "label": k,
            "count": v,
        })
    for k, v in d["tones"].items():
        export_rows.append({
            "ticker": t,
            "company": d["company"],
            "metric": "tone",
            "label": k,
            "count": v,
        })

export_df = pd.DataFrame(export_rows)

st.download_button(
    "Download Company ESG Statistics (CSV)",
    data=export_df.to_csv(index=False),
    file_name="company_esg_absa_stats.csv",
    mime="text/csv",
)
