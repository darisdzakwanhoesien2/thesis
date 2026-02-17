import streamlit as st
import pandas as pd

from core.correction_engine import suggest_gt_corrections

st.set_page_config(layout="wide")
st.title("🛠 Ground Truth Correction Engine")

COMPARE_PATH = "logs/comparison.csv"

if not pd.io.common.file_exists(COMPARE_PATH):
    st.warning("Run comparison first.")
    st.stop()

compare_df = pd.read_csv(COMPARE_PATH)

threshold = st.slider("Confidence Threshold", 0.0, 1.0, 0.85)

suggestions = suggest_gt_corrections(compare_df, threshold)

st.write(f"Suggested Corrections: {len(suggestions)}")

st.dataframe(suggestions, use_container_width=True)

if st.button("Export Suggested Corrections"):
    suggestions.to_csv("logs/suggested_gt_updates.csv", index=False)
    st.success("Exported.")
