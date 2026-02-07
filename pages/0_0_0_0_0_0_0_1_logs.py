import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="PDF Download Logs", layout="wide")

st.title("📋 PDF Download Log Viewer")

LOG_PATH = Path("logs/pdf_download_log.jsonl")

@st.cache_data
def load_logs(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    return pd.DataFrame(records)

if not LOG_PATH.exists():
    st.error("Log file not found!")
    st.stop()

df = load_logs(LOG_PATH)

# Convert timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Extract company from json_file
df["company"] = df["json_file"].str.replace(".json", "", regex=False)

# Sidebar Filters
st.sidebar.header("🔎 Filters")

companies = st.sidebar.multiselect(
    "Select Company",
    options=df["company"].unique(),
    default=df["company"].unique()
)

statuses = st.sidebar.multiselect(
    "Select Status",
    options=df["status"].unique(),
    default=df["status"].unique()
)

filtered_df = df[
    (df["company"].isin(companies)) &
    (df["status"].isin(statuses))
]

st.subheader("📊 Summary")
col1, col2, col3 = st.columns(3)

col1.metric("Total Logs", len(filtered_df))
col2.metric("Total Errors", len(filtered_df[filtered_df["status"] == "error"]))
col3.metric("Unique Companies", filtered_df["company"].nunique())

st.divider()

st.subheader("📋 Log Table")
st.dataframe(
    filtered_df.sort_values("timestamp", ascending=False),
    use_container_width=True
)
