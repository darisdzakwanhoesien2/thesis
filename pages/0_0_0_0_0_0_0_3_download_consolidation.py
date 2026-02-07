import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="Download Consolidation", layout="wide")

st.title("📦 PDF Download Consolidation Dashboard")

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
LOG_PATH = Path("logs/pdf_download_log.jsonl")  # Change if needed

# ------------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------------
@st.cache_data
def load_data(path):
    if path.suffix == ".jsonl":
        df = pd.read_json(path, lines=True)
    else:
        df = pd.read_csv(path)
    return df

if not LOG_PATH.exists():
    st.error("❌ Log file not found!")
    st.stop()

df = load_data(LOG_PATH)

# Clean timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

# Ensure company column exists
if "company" not in df.columns:
    df["company"] = df["json_file"].str.replace(".json", "", regex=False)

# ------------------------------------------------------------------
# SPLIT SUCCESS & NON-SUCCESS
# ------------------------------------------------------------------
success_df = df[df["status"].str.lower() == "success"].copy()
non_success_df = df[df["status"].str.lower() != "success"].copy()

# ------------------------------------------------------------------
# SUMMARY METRICS
# ------------------------------------------------------------------
st.subheader("📊 Overview Summary")

col1, col2, col3 = st.columns(3)

col1.metric("Total Records", len(df))
col2.metric("Successful Downloads", len(success_df))
col3.metric("Failed Downloads", len(non_success_df))

st.divider()

# ------------------------------------------------------------------
# SUCCESS TABLE
# ------------------------------------------------------------------
st.subheader("✅ Successful PDF Downloads")

if success_df.empty:
    st.info("No successful downloads found.")
else:
    st.dataframe(
        success_df.sort_values("timestamp", ascending=False),
        use_container_width=True
    )

    st.download_button(
        label="📥 Download Success CSV",
        data=success_df.to_csv(index=False),
        file_name="successful_downloads.csv",
        mime="text/csv"
    )

st.divider()

# ------------------------------------------------------------------
# NON-SUCCESS TABLE
# ------------------------------------------------------------------
st.subheader("❌ Non-Successful PDF Downloads")

if non_success_df.empty:
    st.success("No errors detected 🎉")
else:
    st.dataframe(
        non_success_df.sort_values("timestamp", ascending=False),
        use_container_width=True
    )

    st.download_button(
        label="📥 Download Failed CSV",
        data=non_success_df.to_csv(index=False),
        file_name="failed_downloads.csv",
        mime="text/csv"
    )

st.divider()

# ------------------------------------------------------------------
# OPTIONAL: Error Breakdown
# ------------------------------------------------------------------
st.subheader("📌 Error Breakdown")

if not non_success_df.empty:
    error_counts = non_success_df["error"].value_counts()
    st.bar_chart(error_counts)
else:
    st.info("No errors to analyze.")
