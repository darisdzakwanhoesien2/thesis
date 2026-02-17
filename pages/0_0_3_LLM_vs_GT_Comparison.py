import streamlit as st
import pandas as pd

from core.comparison import compare_with_gt

st.set_page_config(layout="wide")
st.title("🔍 LLM vs Ground Truth Comparison")

LLM_PATH = "logs/llm_processed.csv"
GT_PATH = "data/ground_truth/absa_mapping.csv"

if not pd.io.common.file_exists(LLM_PATH):
    st.warning("No LLM results found.")
    st.stop()

llm_df = pd.read_csv(LLM_PATH)
gt_df = pd.read_csv(GT_PATH)

compare_df = compare_with_gt(llm_df, gt_df)

st.metric("Full Match Rate", f"{compare_df['full_match'].mean():.3f}")

st.dataframe(compare_df, use_container_width=True)

st.download_button(
    "Download Comparison",
    compare_df.to_csv(index=False),
    "comparison.csv"
)
