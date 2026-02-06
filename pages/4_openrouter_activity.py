import streamlit as st
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import os

# =====================================================
# PATH + ENV
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY not found in .env")
    st.stop()

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📊 OpenRouter Activity Dashboard")

st.caption("Data pulled from OpenRouter Analytics API")

# =====================================================
# API CALL
# =====================================================

API_URL = "https://openrouter.ai/api/v1/activity"

@st.cache_data(ttl=300)  # cache for 5 minutes
def fetch_activity(date=None):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    params = {}
    if date:
        params["datestring"] = date

    r = requests.get(API_URL, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

# =====================================================
# DATE FILTER
# =====================================================

st.sidebar.header("🗓 Date Filter")

use_date = st.sidebar.checkbox("Filter by date")

date_val = None
if use_date:
    date_val = st.sidebar.date_input("Select date").strftime("%Y-%m-%d")

# =====================================================
# LOAD DATA
# =====================================================

try:
    data = fetch_activity(date_val)
except Exception as e:
    st.error(f"❌ Failed to fetch activity:\n{e}")
    st.stop()

rows = data.get("data", [])

if not rows:
    st.warning("No activity data returned.")
    st.stop()

df = pd.DataFrame(rows)

st.success(f"Loaded {len(df)} activity records")

# =====================================================
# CLEAN TYPES
# =====================================================

num_cols = [
    "usage",
    "byok_usage_inference",
    "requests",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
]

for c in num_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

# =====================================================
# RAW TABLE
# =====================================================

with st.expander("📄 Raw Activity Table"):
    st.dataframe(df, use_container_width=True)

# =====================================================
# METRICS
# =====================================================

st.subheader("📌 Overall Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Requests", int(df["requests"].sum()))
col2.metric("Prompt Tokens", int(df["prompt_tokens"].sum()))
col3.metric("Completion Tokens", int(df["completion_tokens"].sum()))
col4.metric("Total Usage ($)", round(df["usage"].sum(), 4))

# =====================================================
# REQUESTS PER DAY
# =====================================================

st.subheader("📆 Requests per Day")

req_by_day = (
    df.groupby("date")["requests"]
    .sum()
    .sort_index()
)

st.line_chart(req_by_day)

# =====================================================
# TOKENS PER MODEL
# =====================================================

st.subheader("🤖 Token Usage per Model")

df["total_tokens"] = df["prompt_tokens"] + df["completion_tokens"]

tok_by_model = (
    df.groupby("model")["total_tokens"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(tok_by_model)

# =====================================================
# REQUESTS PER PROVIDER
# =====================================================

if "provider_name" in df.columns:
    st.subheader("🏢 Requests per Provider")

    prov = (
        df.groupby("provider_name")["requests"]
        .sum()
        .sort_values(ascending=False)
    )

    st.bar_chart(prov)

# =====================================================
# COST PER MODEL
# =====================================================

st.subheader("💸 Cost per Model ($)")

cost_by_model = (
    df.groupby("model")["usage"]
    .sum()
    .sort_values(ascending=False)
)

st.bar_chart(cost_by_model)

# =====================================================
# EXPORT
# =====================================================

st.subheader("⬇️ Export")

csv = df.to_csv(index=False)

st.download_button(
    "Download CSV",
    data=csv,
    file_name="openrouter_activity.csv",
    mime="text/csv",
)
