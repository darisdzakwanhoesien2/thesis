import streamlit as st
import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("📊 ABSA Multi-Batch Experiment Dashboard")

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"

# =====================================================
# LOAD FILES
# =====================================================

log_files = list(LOGS_DIR.glob("absa_*.json"))

if not log_files:
    st.warning("No ABSA experiment logs found in logs/")
    st.stop()

# =====================================================
# FILENAME PARSER
# =====================================================

def parse_filename(fname):
    name = fname.replace(".json", "")

    # timestamp
    ts_match = re.search(r"absa_(\d{8}_\d{6})_", name)
    timestamp = ts_match.group(1) if ts_match else None

    # method
    method_match = re.search(r"_absa_indonesia_(.*?)_", name)
    method = method_match.group(1) if method_match else None

    # model
    model_match = re.search(r"_absa_indonesia_.*?_(.*)__Free_", name)
    model = model_match.group(1) if model_match else None

    # report
    report_match = re.search(
        r"\d{8}_\d{6}_(.*?)_absa_indonesia_",
        name
    )
    report = report_match.group(1) if report_match else None

    batch_date = timestamp[:8] if timestamp else None

    return timestamp, batch_date, report, method, model


# =====================================================
# BUILD DATAFRAME
# =====================================================

records = []

for file in log_files:
    timestamp, batch_date, report, method, model = parse_filename(file.name)

    try:
        with open(file, "r", encoding="utf-8") as f:
            log = json.load(f)
            output = log.get("output", "")
    except:
        output = ""

    records.append({
        "filename": file.name,
        "timestamp": timestamp,
        "batch_date": batch_date,
        "report": report,
        "method": method,
        "model": model,
        "output_length": len(output),
        "aspect_mentions": len(re.findall(r"aspect", output.lower())),
        "sentiment_mentions": len(re.findall(r"sentiment", output.lower()))
    })

df = pd.DataFrame(records)

if df.empty:
    st.warning("No valid experiment data found.")
    st.stop()

# =====================================================
# SIDEBAR FILTERS
# =====================================================

st.sidebar.header("🔎 Filters")

selected_reports = st.sidebar.multiselect(
    "Select Reports",
    sorted(df["report"].dropna().unique()),
    default=sorted(df["report"].dropna().unique())
)

selected_methods = st.sidebar.multiselect(
    "Select Methods",
    sorted(df["method"].dropna().unique()),
    default=sorted(df["method"].dropna().unique())
)

selected_models = st.sidebar.multiselect(
    "Select Models",
    sorted(df["model"].dropna().unique()),
    default=sorted(df["model"].dropna().unique())
)

filtered_df = df[
    (df["report"].isin(selected_reports)) &
    (df["method"].isin(selected_methods)) &
    (df["model"].isin(selected_models))
]

# =====================================================
# OVERVIEW METRICS
# =====================================================

st.subheader("📈 Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Runs", len(filtered_df))
col2.metric("Reports", filtered_df["report"].nunique())
col3.metric("Methods", filtered_df["method"].nunique())
col4.metric("Models", filtered_df["model"].nunique())

# =====================================================
# METHOD COMPARISON
# =====================================================

st.subheader("🧠 Method Comparison (Avg Output Length)")

method_stats = (
    filtered_df
    .groupby("method")["output_length"]
    .mean()
    .sort_values(ascending=False)
)

st.bar_chart(method_stats)

# =====================================================
# MODEL COMPARISON
# =====================================================

st.subheader("🤖 Model Comparison (Avg Output Length)")

model_stats = (
    filtered_df
    .groupby("model")["output_length"]
    .mean()
    .sort_values(ascending=False)
)

st.bar_chart(model_stats)

# =====================================================
# METHOD × MODEL MATRIX
# =====================================================

st.subheader("📊 Method × Model Matrix")

pivot = filtered_df.pivot_table(
    index="method",
    columns="model",
    values="output_length",
    aggfunc="mean"
)

st.dataframe(pivot)

# =====================================================
# REPORT COVERAGE
# =====================================================

st.subheader("📄 Runs per Report")

report_counts = filtered_df["report"].value_counts()
st.bar_chart(report_counts)

# =====================================================
# BATCH DISTRIBUTION
# =====================================================

st.subheader("📦 Runs per Batch Date")

batch_counts = filtered_df["batch_date"].value_counts()
st.bar_chart(batch_counts)

# =====================================================
# ASPECT / SENTIMENT SIGNALS
# =====================================================

st.subheader("🧩 Aspect & Sentiment Signal Comparison")

signal_stats = (
    filtered_df
    .groupby("method")[["aspect_mentions", "sentiment_mentions"]]
    .mean()
)

st.dataframe(signal_stats)

# =====================================================
# RAW TABLE
# =====================================================

st.subheader("📋 Full Experiment Table")

st.dataframe(filtered_df.sort_values("timestamp"))

# =====================================================
# EXPORT CSV
# =====================================================

csv = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Filtered CSV",
    csv,
    "absa_experiment_results.csv",
    "text/csv"
)


# import streamlit as st
# import pandas as pd
# import json
# from pathlib import Path
# import os
# import re

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# LOGS_DIR = BASE_DIR / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"

# st.set_page_config(layout="wide")
# st.title("📊 ABSA Experiment Dashboard")

# # =====================================================
# # LOAD LOG FILES
# # =====================================================

# log_files = list(LOGS_DIR.glob("bulk_absa_*.json"))

# if not log_files:
#     st.warning("No experiment logs found.")
#     st.stop()

# data = []

# for file in log_files:
#     try:
#         with open(file, "r", encoding="utf-8") as f:
#             log = json.load(f)

#         output = log.get("output", "")

#         data.append({
#             "timestamp": log.get("timestamp"),
#             "pdf": log.get("pdf"),
#             "prompt": log.get("prompt_file"),
#             "model": log.get("model"),
#             "temperature": log.get("temperature"),
#             "max_tokens": log.get("max_tokens"),
#             "pages_count": len(log.get("pages", [])),
#             "output_length": len(output),
#             "aspect_mentions": len(re.findall(r"aspect", output.lower())),
#             "sentiment_mentions": len(re.findall(r"sentiment", output.lower())),
#         })

#     except:
#         continue

# df = pd.DataFrame(data)

# if df.empty:
#     st.warning("No valid logs found.")
#     st.stop()

# # =====================================================
# # BASIC METRICS
# # =====================================================

# st.subheader("📈 Overview Metrics")

# col1, col2, col3, col4 = st.columns(4)

# col1.metric("Total Runs", len(df))
# col2.metric("Unique PDFs", df["pdf"].nunique())
# col3.metric("Prompt Methods", df["prompt"].nunique())
# col4.metric("Models Used", df["model"].nunique())

# # =====================================================
# # PROMPT COMPARISON
# # =====================================================

# st.subheader("🧠 Prompt Comparison")

# prompt_stats = df.groupby("prompt").agg({
#     "output_length": "mean",
#     "aspect_mentions": "mean",
#     "sentiment_mentions": "mean"
# }).reset_index()

# st.dataframe(prompt_stats)

# st.bar_chart(prompt_stats.set_index("prompt")["output_length"])

# # =====================================================
# # MODEL USAGE
# # =====================================================

# st.subheader("🤖 Model Usage Distribution")

# model_counts = df["model"].value_counts()
# st.bar_chart(model_counts)

# # =====================================================
# # PDF COVERAGE
# # =====================================================

# st.subheader("📄 PDF Coverage")

# pdf_counts = df["pdf"].value_counts()
# st.bar_chart(pdf_counts)

# # =====================================================
# # EXPERIMENT SETS
# # =====================================================

# st.subheader("🧪 Experiment Sets")

# if REGISTRY_PATH.exists():
#     with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#         registry = json.load(f)

#     sets = registry.get("sets", {})

#     if sets:
#         for set_name, files in sets.items():
#             st.markdown(f"### {set_name}")
#             st.write(f"{len(files)} runs")
#             st.code(files)
#     else:
#         st.info("No experiment sets found.")
# else:
#     st.info("registry.json not found.")
