import streamlit as st
import pandas as pd
from pathlib import Path
from io import StringIO
import csv
import json
from datetime import datetime

DATA_PATH = Path("data/ground_truth_windows/absa_mapping.csv")
# DATA_PATH = Path("data/master_dataset.csv")
FAILED_LOG_PATH = Path("logs/failed_rows.json")

COLUMNS = [
    "sentence_norm",
    "canonical_aspect",
    "majority_category",
    "majority_sentiment",
    "majority_tone",
    "runs_count"
]

# =====================================
# Utilities
# =====================================
def load_master():
    if DATA_PATH.exists():
        df = pd.read_csv(DATA_PATH)
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        return df
    return pd.DataFrame(columns=COLUMNS)

def save_master(df):
    df.to_csv(DATA_PATH, index=False)

def log_failed(rows):
    if FAILED_LOG_PATH.exists():
        logs = json.load(open(FAILED_LOG_PATH))
    else:
        logs = []

    logs.extend(rows)

    with open(FAILED_LOG_PATH, "w") as f:
        json.dump(logs, f, indent=4)

# =====================================
# UI
# =====================================
st.title("📥 Robust Bulk Insert (Text Mode)")

raw_text = st.text_area(
    "Paste CSV Content Here",
    height=300
)

if st.button("Parse & Save"):

    lines = raw_text.strip().split("\n")

    if len(lines) < 2:
        st.error("Not enough rows.")
        st.stop()

    reader = csv.reader(lines)

    header = next(reader)

    successful_rows = []
    failed_rows = []

    for idx, row in enumerate(reader, start=2):

        if len(row) != len(COLUMNS):
            failed_rows.append({
                "line_number": idx,
                "raw_data": row,
                "reason": f"Expected {len(COLUMNS)} columns, got {len(row)}",
                "timestamp": str(datetime.now())
            })
            continue

        try:
            entry = dict(zip(COLUMNS, row))
            entry["runs_count"] = int(entry["runs_count"])

            successful_rows.append(entry)

        except Exception as e:
            failed_rows.append({
                "line_number": idx,
                "raw_data": row,
                "reason": str(e),
                "timestamp": str(datetime.now())
            })

    # =====================================
    # Save successful rows
    # =====================================
    if successful_rows:
        df_master = load_master()
        df_new = pd.DataFrame(successful_rows)
        df_final = pd.concat([df_master, df_new], ignore_index=True)
        save_master(df_final)

    # =====================================
    # Save failed rows to JSON
    # =====================================
    if failed_rows:
        log_failed(failed_rows)

    # =====================================
    # Report
    # =====================================
    st.success(f"✅ {len(successful_rows)} rows inserted successfully.")
    st.warning(f"⚠️ {len(failed_rows)} rows failed and stored in failed_rows.json")

    if successful_rows:
        st.subheader("Successful Rows Preview")
        st.dataframe(pd.DataFrame(successful_rows))

    if failed_rows:
        st.subheader("Failed Rows")
        st.json(failed_rows)


# import streamlit as st
# import pandas as pd
# from pathlib import Path
# from io import StringIO

# DATA_PATH = Path("data/master_dataset.csv")

# COLUMNS = [
#     "sentence_norm",
#     "canonical_aspect",
#     "majority_category",
#     "majority_sentiment",
#     "majority_tone",
#     "runs_count"
# ]

# # =====================================
# # Load Existing Dataset
# # =====================================
# def load_master():
#     if DATA_PATH.exists():
#         df = pd.read_csv(DATA_PATH)
#         df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
#         return df
#     return pd.DataFrame(columns=COLUMNS)

# def save_master(df):
#     df.to_csv(DATA_PATH, index=False)

# # =====================================
# # UI
# # =====================================
# st.title("📥 Bulk Insert ESG Data (Text Mode)")

# mode = st.radio(
#     "Choose Input Mode",
#     ["Paste CSV Text", "Upload CSV File"]
# )

# df_new = None

# # =====================================
# # TEXT MODE
# # =====================================
# if mode == "Paste CSV Text":

#     raw_text = st.text_area(
#         "Paste CSV Content Here",
#         height=300,
#         placeholder="sentence_norm,canonical_aspect,majority_category,majority_sentiment,majority_tone,runs_count\n..."
#     )

#     if st.button("Parse Text"):
#         try:
#             df_new = pd.read_csv(StringIO(raw_text))

#             # Remove empty unnamed columns
#             df_new = df_new.loc[:, ~df_new.columns.str.contains("^Unnamed")]

#             # Keep only required columns
#             df_new = df_new[COLUMNS]

#             df_new = df_new.fillna("")

#             st.success("Parsed Successfully!")
#             st.dataframe(df_new)

#         except Exception as e:
#             st.error(f"Parsing failed: {e}")

# # =====================================
# # FILE MODE (Optional fallback)
# # =====================================
# if mode == "Upload CSV File":
#     uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

#     if uploaded_file:
#         df_new = pd.read_csv(uploaded_file)
#         df_new = df_new.loc[:, ~df_new.columns.str.contains("^Unnamed")]
#         df_new = df_new[COLUMNS]
#         df_new = df_new.fillna("")
#         st.dataframe(df_new)

# # =====================================
# # SAVE SECTION
# # =====================================
# if df_new is not None:

#     save_option = st.radio(
#         "Save Mode",
#         ["Append to Master Dataset", "Overwrite Master Dataset"]
#     )

#     if st.button("Save to Master Dataset"):

#         df_master = load_master()

#         if save_option == "Append to Master Dataset":
#             df_final = pd.concat([df_master, df_new], ignore_index=True)
#         else:
#             df_final = df_new

#         save_master(df_final)

#         st.success("Dataset Saved Successfully!")

#         st.dataframe(df_final)


# import streamlit as st
# import pandas as pd
# from pathlib import Path

# DATA_PATH = Path("data/ground_truth_windows/absa_mapping.csv")

# COLUMNS = [
#     "sentence_norm",
#     "canonical_aspect",
#     "majority_category",
#     "majority_sentiment",
#     "majority_tone",
#     "runs_count"
# ]

# st.title("📥 Bulk Upload & Clean")

# uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

# if uploaded_file:
#     df = pd.read_csv(uploaded_file)

#     # Remove unnamed columns
#     df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

#     # Keep required columns
#     df = df[COLUMNS]

#     df = df.fillna("")

#     if st.button("Save to Master Dataset"):
#         df.to_csv(DATA_PATH, index=False)
#         st.success("Dataset saved successfully!")

#     st.dataframe(df)
