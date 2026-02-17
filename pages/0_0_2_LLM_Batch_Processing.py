import streamlit as st
import pandas as pd
import uuid
import os

from core.prompt_builder import build_batch_prompt
from core.lm_client import call_lmstudio_batch
from core.validator import validate

st.set_page_config(layout="wide")
st.title("🤖 LLM Batch Processing")

BATCH_SIZE = 5
PROCESSED_PATH = "logs/llm_processed.csv"

# Load unmatched pairs
fp_df = pd.read_csv("logs/false_positives.csv") if os.path.exists("logs/false_positives.csv") else pd.DataFrame()
fn_df = pd.read_csv("logs/false_negatives.csv") if os.path.exists("logs/false_negatives.csv") else pd.DataFrame()

review_df = pd.concat([fp_df, fn_df], ignore_index=True)

if review_df.empty:
    st.warning("No unmatched pairs found.")
    st.stop()

# Deterministic ID (important for resume!)
review_df["id"] = review_df.apply(
    lambda x: f"{x['sentence_norm']}||{x['canonical_aspect']}",
    axis=1
)

# Resume logic
if os.path.exists(PROCESSED_PATH):
    processed_df = pd.read_csv(PROCESSED_PATH)
    review_df = review_df[
        ~review_df["id"].isin(processed_df["id"])
    ]
else:
    processed_df = pd.DataFrame()

st.write(f"Remaining samples: {len(review_df)}")

if st.button("Run Batch LLM Processing"):

    results = []

    for i in range(0, len(review_df), BATCH_SIZE):

        batch = review_df.iloc[i:i+BATCH_SIZE]
        prompt = build_batch_prompt(batch.to_dict("records"))

        output = call_lmstudio_batch(prompt)

        for item in output:
            validated = validate(item)
            original = batch[batch["id"] == item["id"]].iloc[0]

            validated.update({
                "id": original["id"],
                "sentence_norm": original["sentence_norm"],
                "canonical_aspect": original["canonical_aspect"]
            })

            results.append(validated)

    result_df = pd.DataFrame(results)

    final_df = pd.concat([processed_df, result_df], ignore_index=True)
    final_df.to_csv(PROCESSED_PATH, index=False)

    st.success("Processing complete!")
