import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.set_page_config(page_title="Error Analytics", layout="wide")

st.title("📊 PDF Download Error Analytics")

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
df["timestamp"] = pd.to_datetime(df["timestamp"])
df["company"] = df["json_file"].str.replace(".json", "", regex=False)

error_df = df[df["status"] == "error"]

st.subheader("📌 Errors per Company")
company_counts = error_df["company"].value_counts()
st.bar_chart(company_counts)

st.subheader("📌 Errors per Year (based on title)")
error_df["year"] = error_df["title"].str.extract(r"(\d{4})")

year_counts = error_df["year"].value_counts().sort_index()
st.bar_chart(year_counts)

st.subheader("📌 Error Messages Breakdown")
error_message_counts = error_df["error"].value_counts()
st.dataframe(error_message_counts)
