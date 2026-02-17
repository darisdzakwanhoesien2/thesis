import streamlit as st
from pathlib import Path
import json
import pandas as pd

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

# =====================================================
# REPO ROOT DISCOVERY
# =====================================================

def find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for parent in [start] + list(start.parents):
        if (parent / "logs").exists() or (parent / "data").exists():
            return parent
    return start

PROJECT_ROOT = find_repo_root(Path.cwd())

LOGS_DIR = PROJECT_ROOT / "logs"
REGISTRY_PATH = LOGS_DIR / "registry.json"
MAPPING_PATH = PROJECT_ROOT / "data" / "aspect_mapping.json"
GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "absa_mapping.csv"

# =====================================================
# VALIDATE REQUIRED FILES
# =====================================================

for p in [REGISTRY_PATH, MAPPING_PATH, GT_PATH]:
    if not p.exists():
        st.error(f"Missing required file: {p}")
        st.stop()

# =====================================================
# SAFE JSON LOADER
# =====================================================

def safe_json_load(text):
    try:
        return json.loads(text)
    except:
        pass

    objects, buf, depth = [], "", 0
    for ch in text:
        if ch == "{":
            depth += 1
        if depth > 0:
            buf += ch
        if ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    objects.append(json.loads(buf))
                except:
                    pass
                buf = ""
    return objects

# =====================================================
# LOAD ASPECT MAPPING
# =====================================================

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

ASPECT_MAP = {}
for group in mapping_cfg.get("mappings", []):
    canonical = group["canonical"].lower().strip()
    for alias in group["aliases"]:
        ASPECT_MAP[alias.lower().strip()] = canonical

# =====================================================
# LOAD REGISTRY
# =====================================================

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

sets = registry.get("sets", {})
if not sets:
    st.error("No experiment sets found.")
    st.stop()

# =====================================================
# COLLECT ALL LOG FILES
# =====================================================

all_files = set()
for files in sets.values():
    all_files.update(files)

# =====================================================
# LOAD PREDICTIONS
# =====================================================

rows = []

for fname in all_files:

    path = LOGS_DIR / fname
    if not path.exists():
        continue

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        continue

    parsed = safe_json_load(data.get("output", ""))

    for it in parsed:
        if not isinstance(it, dict):
            continue

        sent = it.get("sentence")
        asp = it.get("aspect")

        if not sent or not asp:
            continue

        asp_norm = str(asp).lower().strip()
        asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

        rows.append({
            "sentence_norm": " ".join(str(sent).split()),
            "canonical_aspect": asp_map,
            "aspect_category": str(it.get("aspect_category", "")).lower().strip(),
            "sentiment": str(it.get("sentiment", "")).lower().strip(),
            "tone": str(it.get("tone", "")).lower().strip(),
        })

if not rows:
    st.error("No prediction data found.")
    st.stop()

raw_df = pd.DataFrame(rows)

# =====================================================
# AGGREGATE MAJORITY VOTE
# =====================================================

combined = []

for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):
    combined.append({
        "sentence_norm": sent,
        "canonical_aspect": asp,
        "majority_category": g["aspect_category"].mode().iloc[0] if not g["aspect_category"].mode().empty else "",
        "majority_sentiment": g["sentiment"].mode().iloc[0] if not g["sentiment"].mode().empty else "",
        "majority_tone": g["tone"].mode().iloc[0] if not g["tone"].mode().empty else "",
    })

pred_df = pd.DataFrame(combined)

# =====================================================
# LOAD GROUND TRUTH (AUTO DETECT ALL FORMATS)
# =====================================================

gt_df = pd.read_csv(GT_PATH)

# Remove index column caused by leading comma
gt_df = gt_df.loc[:, ~gt_df.columns.str.contains("^Unnamed")]
gt_df = gt_df.dropna(axis=1, how="all")

columns = set(gt_df.columns)

STANDARD_GT = {
    "sentence",
    "canonical_aspect",
    "aspect_categories",
    "sentiments",
    "tones",
}

AGGREGATED_GT = {
    "sentence_norm",
    "canonical_aspect",
    "majority_category",
    "majority_sentiment",
    "majority_tone",
}

if STANDARD_GT.issubset(columns):
    st.info("Standard Ground Truth Format Detected")
    gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()

elif AGGREGATED_GT.issubset(columns):
    st.info("Aggregated Prediction-Style Format Detected")

    gt_df = gt_df.rename(columns={
        "majority_category": "aspect_categories",
        "majority_sentiment": "sentiments",
        "majority_tone": "tones",
    })

else:
    st.error(f"Unknown ground truth format. Found columns: {columns}")
    st.stop()

# ESG Code Mapping
CATEGORY_MAP = {
    "e": "environment",
    "s": "social",
    "g": "governance"
}

gt_df["aspect_categories"] = (
    gt_df["aspect_categories"]
    .astype(str)
    .str.lower()
    .str.strip()
    .map(lambda x: CATEGORY_MAP.get(x, x))
)

gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()
gt_df["sentence_norm"] = gt_df["sentence_norm"].astype(str).str.strip()

gt_df = gt_df.drop_duplicates(["sentence_norm", "canonical_aspect"])

# =====================================================
# ASPECT DETECTION METRICS
# =====================================================

gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

tp = len(gt_pairs & pred_pairs)
fp = len(pred_pairs - gt_pairs)
fn = len(gt_pairs - pred_pairs)

precision = tp / (tp + fp + 1e-9)
recall = tp / (tp + fn + 1e-9)
f1 = 2 * precision * recall / (precision + recall + 1e-9)

st.subheader("Aspect Detection Performance")

c1, c2, c3, c4 = st.columns(4)
c1.metric("TP", tp)
c2.metric("FP", fp)
c3.metric("FN", fn)
c4.metric("F1", f"{f1:.3f}")

st.write(f"Precision: {precision:.3f}")
st.write(f"Recall: {recall:.3f}")

# =====================================================
# LABEL EVALUATION
# =====================================================

eval_df = pd.merge(
    gt_df,
    pred_df,
    on=["sentence_norm", "canonical_aspect"],
    how="inner"
)

def accuracy(gt, pred):
    if len(gt) == 0:
        return 0.0
    return (gt == pred).mean()

st.subheader("Classification Accuracy")

st.metric("Aspect Category",
          f"{accuracy(eval_df['aspect_categories'], eval_df['majority_category']):.3f}")

st.metric("Sentiment",
          f"{accuracy(eval_df['sentiments'], eval_df['majority_sentiment']):.3f}")

st.metric("Tone",
          f"{accuracy(eval_df['tones'], eval_df['majority_tone']):.3f}")

# =====================================================
# DETAILED ERROR ANALYSIS
# =====================================================

st.markdown("---")
st.header("🔎 Detailed Evaluation Breakdown")

# -----------------------------------------------------
# MATCHED DATA (for classification evaluation)
# -----------------------------------------------------

if len(eval_df) == 0:
    st.warning("No matched sentence-aspect pairs found.")
else:

    # -------------------------------
    # CORRECT PREDICTIONS
    # -------------------------------

    correct_df = eval_df[
        (eval_df["aspect_categories"] == eval_df["majority_category"]) &
        (eval_df["sentiments"] == eval_df["majority_sentiment"]) &
        (eval_df["tones"] == eval_df["majority_tone"])
    ]

    # -------------------------------
    # INCORRECT PREDICTIONS
    # -------------------------------

    incorrect_df = eval_df[
        (eval_df["aspect_categories"] != eval_df["majority_category"]) |
        (eval_df["sentiments"] != eval_df["majority_sentiment"]) |
        (eval_df["tones"] != eval_df["majority_tone"])
    ]

    # -------------------------------
    # SUMMARY METRICS
    # -------------------------------

    c1, c2 = st.columns(2)
    c1.metric("✅ Correct Predictions", len(correct_df))
    c2.metric("❌ Incorrect Predictions", len(incorrect_df))

    # -------------------------------
    # CORRECT TABLE
    # -------------------------------

    with st.expander("✅ View Correct Predictions"):
        st.dataframe(
            correct_df[
                [
                    "sentence_norm",
                    "canonical_aspect",
                    "aspect_categories",
                    "sentiments",
                    "tones",
                ]
            ],
            use_container_width=True,
        )

        st.download_button(
            "Download Correct Predictions",
            correct_df.to_csv(index=False).encode("utf-8"),
            "correct_predictions.csv",
            mime="text/csv",
        )

    # -------------------------------
    # INCORRECT TABLE
    # -------------------------------

    with st.expander("❌ View Incorrect Predictions"):
        st.dataframe(
            incorrect_df[
                [
                    "sentence_norm",
                    "canonical_aspect",
                    "aspect_categories", "majority_category",
                    "sentiments", "majority_sentiment",
                    "tones", "majority_tone",
                ]
            ],
            use_container_width=True,
        )

        st.download_button(
            "Download Incorrect Predictions",
            incorrect_df.to_csv(index=False).encode("utf-8"),
            "incorrect_predictions.csv",
            mime="text/csv",
        )

# =====================================================
# UNMATCHED ANALYSIS (FP & FN)
# =====================================================

st.markdown("---")
st.header("🚫 Unmatched Aspect Pairs")

# Recompute for clarity
gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

fp_pairs = pred_pairs - gt_pairs
fn_pairs = gt_pairs - pred_pairs

# Convert to DataFrames
fp_df = pd.DataFrame(list(fp_pairs), columns=["sentence_norm", "canonical_aspect"])
fn_df = pd.DataFrame(list(fn_pairs), columns=["sentence_norm", "canonical_aspect"])

c1, c2 = st.columns(2)
c1.metric("🚫 False Positives (Predicted but not in GT)", len(fp_df))
c2.metric("🚫 False Negatives (Missed GT Aspects)", len(fn_df))

# -------------------------------
# FALSE POSITIVES
# -------------------------------

with st.expander("🚫 View False Positives"):
    if not fp_df.empty:
        st.dataframe(fp_df, use_container_width=True)
        st.download_button(
            "Download False Positives",
            fp_df.to_csv(index=False).encode("utf-8"),
            "false_positives.csv",
            mime="text/csv",
        )
    else:
        st.success("No false positives 🎉")

# -------------------------------
# FALSE NEGATIVES
# -------------------------------

with st.expander("🚫 View False Negatives"):
    if not fn_df.empty:
        st.dataframe(fn_df, use_container_width=True)
        st.download_button(
            "Download False Negatives",
            fn_df.to_csv(index=False).encode("utf-8"),
            "false_negatives.csv",
            mime="text/csv",
        )
    else:
        st.success("No false negatives 🎉")


# =====================================================
# DOWNLOAD RESULTS
# =====================================================

with st.expander("Download Evaluation Results"):
    st.download_button(
        "Download Evaluation CSV",
        eval_df.to_csv(index=False).encode("utf-8"),
        "absa_evaluation.csv",
        mime="text/csv"
    )

# =====================================================
# 🤖 SAFE LLM PROCESSING (DEBUG MODE)
# =====================================================

import requests
import time
from datetime import datetime

st.markdown("---")
st.header("🤖 LLM Processing (Debug Enabled)")

LM_URL = "http://localhost:1234/v1/chat/completions"
LM_MODEL = "local-model"

LLM_SAVE_PATH = LOGS_DIR / "llm_unmatched_results.csv"
LLM_DEBUG_PATH = LOGS_DIR / "llm_debug_log.json"

# -----------------------------------------------------
# Combine FP + FN
# -----------------------------------------------------

review_df = pd.concat([fp_df, fn_df], ignore_index=True)

if review_df.empty:
    st.success("No unmatched pairs to process 🎉")
    st.stop()

review_df["id"] = review_df.apply(
    lambda x: f"{x['sentence_norm']}||{x['canonical_aspect']}",
    axis=1
)

# -----------------------------------------------------
# Load Already Processed
# -----------------------------------------------------

if LLM_SAVE_PATH.exists():
    processed_df = pd.read_csv(LLM_SAVE_PATH)
    processed_ids = set(processed_df["id"])
else:
    processed_df = pd.DataFrame()
    processed_ids = set()

remaining_df = review_df[~review_df["id"].isin(processed_ids)]

st.subheader("📊 Processing Overview")

c1, c2 = st.columns(2)
c1.metric("Total Unmatched", len(review_df))
c2.metric("Remaining To Process", len(remaining_df))

with st.expander("View Remaining Samples"):
    st.dataframe(remaining_df[["sentence_norm", "canonical_aspect"]])

rows_to_process = st.number_input(
    "How many rows to process now?",
    min_value=1,
    max_value=len(remaining_df) if len(remaining_df) > 0 else 1,
    value=min(3, len(remaining_df)) if len(remaining_df) > 0 else 1
)

# -----------------------------------------------------
# Prompt Builder
# -----------------------------------------------------

def build_prompt(sentence, aspect):
    return f"""
You are an ESG annotation validator.

Sentence:
"{sentence}"

Aspect:
"{aspect}"

Return STRICT JSON:

{{
  "aspect_categories": "...",
  "sentiment": "...",
  "tones": "...",
  "confidence": 0.0,
  "reasoning": "..."
}}
"""

# -----------------------------------------------------
# Safe JSON Extractor
# -----------------------------------------------------

def safe_json_extract(text):

    try:
        return json.loads(text), None
    except Exception as e:

        # Try to extract JSON block manually
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            cleaned = text[start:end]
            return json.loads(cleaned), None
        except Exception as e2:
            return None, str(e2)

# -----------------------------------------------------
# LM Call
# -----------------------------------------------------

def call_lmstudio(prompt):

    try:
        response = requests.post(
            LM_URL,
            json={
                "model": LM_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a strict ESG labeling engine."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 400
            },
            timeout=60
        )

        return response.text

    except Exception as e:
        return f"REQUEST_ERROR: {str(e)}"

# -----------------------------------------------------
# Run Processing
# -----------------------------------------------------

if st.button("🚀 Run LLM Processing"):

    if len(remaining_df) == 0:
        st.warning("Nothing left to process.")
        st.stop()

    batch_df = remaining_df.head(rows_to_process)

    results = []
    debug_logs = []

    progress = st.progress(0)

    for i, row in batch_df.iterrows():

        prompt = build_prompt(row["sentence_norm"], row["canonical_aspect"])

        raw_response = call_lmstudio(prompt)

        parsed_json, parse_error = safe_json_extract(raw_response)

        # Store debug info
        debug_logs.append({
            "timestamp": str(datetime.now()),
            "id": row["id"],
            "prompt": prompt,
            "raw_response": raw_response,
            "parsed_json": parsed_json,
            "parse_error": parse_error
        })

        if parsed_json:

            result = {
                "id": row["id"],
                "sentence_norm": row["sentence_norm"],
                "canonical_aspect": row["canonical_aspect"],
                "aspect_categories": parsed_json.get("aspect_categories", "none"),
                "sentiment": parsed_json.get("sentiment", "none"),
                "tones": parsed_json.get("tones", "none"),
                "confidence": parsed_json.get("confidence", 0),
                "reasoning": parsed_json.get("reasoning", ""),
                "parse_error": ""
            }

        else:

            result = {
                "id": row["id"],
                "sentence_norm": row["sentence_norm"],
                "canonical_aspect": row["canonical_aspect"],
                "aspect_categories": "none",
                "sentiment": "none",
                "tones": "none",
                "confidence": 0,
                "reasoning": "",
                "parse_error": parse_error
            }

        results.append(result)

        progress.progress((len(results)) / len(batch_df))
        time.sleep(0.1)

    # -----------------------------------------------------
    # Save Results
    # -----------------------------------------------------

    new_df = pd.DataFrame(results)
    final_df = pd.concat([processed_df, new_df], ignore_index=True)
    final_df.to_csv(LLM_SAVE_PATH, index=False)

    # Save Debug Logs
    with open(LLM_DEBUG_PATH, "w", encoding="utf-8") as f:
        json.dump(debug_logs, f, indent=2, ensure_ascii=False)

    st.success("Processing complete and saved.")

    st.subheader("🆕 New Results")
    st.dataframe(new_df)

# -----------------------------------------------------
# Show Full History
# -----------------------------------------------------

if LLM_SAVE_PATH.exists():
    st.markdown("---")
    st.subheader("📁 All Processed LLM Results")

    history_df = pd.read_csv(LLM_SAVE_PATH)
    st.dataframe(history_df)

if LLM_DEBUG_PATH.exists():
    st.markdown("---")
    st.subheader("🛠 Debug Log (Last Run)")

    with open(LLM_DEBUG_PATH, "r", encoding="utf-8") as f:
        debug_data = json.load(f)

    st.json(debug_data)

# # =====================================================
# # 🤖 LLM PROCESSING FOR UNMATCHED PAIRS
# # =====================================================

# import requests
# import time

# st.markdown("---")
# st.header("🤖 LLM Processing for Unmatched Aspect Pairs")

# LM_URL = "http://localhost:1234/v1/chat/completions"
# LM_MODEL = "mistralai/ministral-3-3b"   # change if needed
# LLM_SAVE_PATH = LOGS_DIR / "llm_unmatched_results.csv"

# # Combine FP + FN
# review_df = pd.concat([fp_df, fn_df], ignore_index=True)

# if review_df.empty:
#     st.success("No unmatched pairs to process 🎉")
#     st.stop()

# # Create deterministic ID (important for resume)
# review_df["id"] = review_df.apply(
#     lambda x: f"{x['sentence_norm']}||{x['canonical_aspect']}",
#     axis=1
# )

# # Load already processed rows (resume capability)
# if LLM_SAVE_PATH.exists():
#     processed_df = pd.read_csv(LLM_SAVE_PATH)
#     processed_ids = set(processed_df["id"])
# else:
#     processed_df = pd.DataFrame()
#     processed_ids = set()

# # Filter remaining rows
# remaining_df = review_df[~review_df["id"].isin(processed_ids)]

# st.subheader("📊 Processing Overview")

# c1, c2 = st.columns(2)
# c1.metric("Total Unmatched", len(review_df))
# c2.metric("Remaining To Process", len(remaining_df))

# with st.expander("View Remaining Samples"):
#     st.dataframe(remaining_df[["sentence_norm", "canonical_aspect"]], use_container_width=True)

# # User selects how many rows to process
# rows_to_process = st.number_input(
#     "How many rows to process now?",
#     min_value=1,
#     max_value=len(remaining_df) if len(remaining_df) > 0 else 1,
#     value=min(5, len(remaining_df)) if len(remaining_df) > 0 else 1
# )

# def build_prompt(sentence, aspect):
#     return f"""
# You are an ESG annotation validator.

# Sentence:
# "{sentence}"

# Aspect:
# "{aspect}"

# Classify:

# aspect_categories:
# - none
# - social
# - governance
# - environment
# - social-governance
# - environment-social
# - environment-governance
# - environment-social-governance

# sentiment:
# - positive
# - neutral
# - negative
# - none

# tones:
# - commitment
# - action
# - outcome
# - none

# Also give:
# confidence (0 to 1)
# reasoning (short explanation)

# Return STRICT JSON:

# {{
#   "aspect_categories": "...",
#   "sentiment": "...",
#   "tones": "...",
#   "confidence": 0.0,
#   "reasoning": "..."
# }}
# """

# def call_lmstudio(prompt):
#     response = requests.post(
#         LM_URL,
#         json={
#             "model": LM_MODEL,
#             "messages": [
#                 {"role": "system", "content": "You are a strict ESG labeling engine."},
#                 {"role": "user", "content": prompt}
#             ],
#             "temperature": 0,
#             "max_tokens": 400
#         }
#     )
#     return response.json()["choices"][0]["message"]["content"]

# if st.button("🚀 Run LLM Processing"):

#     if len(remaining_df) == 0:
#         st.warning("Nothing left to process.")
#         st.stop()

#     batch_df = remaining_df.head(rows_to_process)

#     results = []
#     progress = st.progress(0)

#     for i, row in batch_df.iterrows():

#         prompt = build_prompt(row["sentence_norm"], row["canonical_aspect"])

#         try:
#             output = call_lmstudio(prompt)
#             parsed = json.loads(output)

#             result = {
#                 "id": row["id"],
#                 "sentence_norm": row["sentence_norm"],
#                 "canonical_aspect": row["canonical_aspect"],
#                 "aspect_categories": parsed.get("aspect_categories", "none"),
#                 "sentiment": parsed.get("sentiment", "none"),
#                 "tones": parsed.get("tones", "none"),
#                 "confidence": float(parsed.get("confidence", 0)),
#                 "reasoning": parsed.get("reasoning", "")
#             }

#         except Exception as e:
#             result = {
#                 "id": row["id"],
#                 "sentence_norm": row["sentence_norm"],
#                 "canonical_aspect": row["canonical_aspect"],
#                 "aspect_categories": "none",
#                 "sentiment": "none",
#                 "tones": "none",
#                 "confidence": 0,
#                 "reasoning": f"ERROR: {e}"
#             }

#         results.append(result)

#         progress.progress((len(results)) / len(batch_df))
#         time.sleep(0.1)

#     new_df = pd.DataFrame(results)

#     # Append to processed
#     final_df = pd.concat([processed_df, new_df], ignore_index=True)
#     final_df.to_csv(LLM_SAVE_PATH, index=False)

#     st.success("Processing complete and saved.")

#     st.dataframe(new_df, use_container_width=True)

# # Show full processed history
# if LLM_SAVE_PATH.exists():
#     st.markdown("---")
#     st.subheader("📁 All Processed LLM Results")

#     history_df = pd.read_csv(LLM_SAVE_PATH)
#     st.dataframe(history_df, use_container_width=True)

#     st.download_button(
#         "Download All LLM Results",
#         history_df.to_csv(index=False).encode("utf-8"),
#         "llm_unmatched_results.csv",
#         mime="text/csv"
#     )


# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

# st.markdown("""
# This page evaluates **all ABSA experiment outputs** against the
# official **ground truth mapping CSV** and reports:

# - ✅ Aspect Detection Precision / Recall / F1
# - 🏷 Aspect Category Accuracy
# - 😊 Sentiment Accuracy
# - 🎯 Tone Accuracy
# - ❌ Detailed False Positives & False Negatives
# - 📥 Downloadable evaluation tables
# """)

# # =====================================================
# # DEPLOYMENT-SAFE PATH DISCOVERY
# # =====================================================

# def find_repo_root(start: Path) -> Path:
#     start = start.resolve()
#     for parent in [start] + list(start.parents):
#         if (parent / "logs").exists() or (parent / "data").exists():
#             return parent
#     return start

# PROJECT_ROOT = find_repo_root(Path.cwd())

# LOGS_DIR = PROJECT_ROOT / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"
# MAPPING_PATH = PROJECT_ROOT / "data" / "aspect_mapping.json"
# GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "absa_mapping.csv"

# # =====================================================
# # VALIDATE FILES
# # =====================================================

# missing = []
# for p in [REGISTRY_PATH, MAPPING_PATH, GT_PATH]:
#     if not p.exists():
#         missing.append(str(p))

# if missing:
#     st.error("❌ Missing required files:")
#     for m in missing:
#         st.code(m)
#     st.stop()

# # =====================================================
# # ROBUST JSON RECOVERY
# # =====================================================

# def recover_json_objects(text):
#     objects, buf, depth, in_obj = [], "", 0, False
#     for ch in text:
#         if ch == "{":
#             depth += 1
#             in_obj = True
#         if in_obj:
#             buf += ch
#         if ch == "}":
#             depth -= 1
#             if depth == 0 and buf:
#                 try:
#                     objects.append(json.loads(buf))
#                 except Exception:
#                     pass
#                 buf, in_obj = "", False
#     return objects


# def extract_json_arrays(text):
#     arrays, stack, start = [], [], None
#     for i, ch in enumerate(text):
#         if ch == "[":
#             if not stack:
#                 start = i
#             stack.append(ch)
#         elif ch == "]" and stack:
#             stack.pop()
#             if not stack and start is not None:
#                 arrays.append(text[start:i+1])
#                 start = None
#     return arrays


# def safe_json_load(text):
#     for arr in reversed(extract_json_arrays(text)):
#         try:
#             return json.loads(arr)
#         except Exception:
#             continue
#     return recover_json_objects(text)

# # =====================================================
# # LOAD ASPECT MAPPING
# # =====================================================

# with open(MAPPING_PATH, "r", encoding="utf-8") as f:
#     mapping_cfg = json.load(f)

# ASPECT_MAP = {}
# for group in mapping_cfg.get("mappings", []):
#     canonical = group["canonical"].lower().strip()
#     for alias in group["aliases"]:
#         ASPECT_MAP[alias.lower().strip()] = canonical

# # =====================================================
# # LOAD REGISTRY
# # =====================================================

# with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#     registry = json.load(f)

# sets = registry.get("sets", {})
# if not sets:
#     st.warning("⚠️ Registry contains no experiment sets.")
#     st.stop()

# # =====================================================
# # COLLECT LOG FILES
# # =====================================================

# all_log_files = set()
# file_to_sets = {}

# for set_name, files in sets.items():
#     for f in files:
#         all_log_files.add(f)
#         file_to_sets.setdefault(f, []).append(set_name)

# st.sidebar.metric("Experiment Sets", len(sets))
# st.sidebar.metric("Total Runs", len(all_log_files))

# # =====================================================
# # LOAD & NORMALIZE ALL RUNS
# # =====================================================

# rows = []
# progress = st.progress(0.0)

# for i, fname in enumerate(sorted(all_log_files), start=1):

#     path = LOGS_DIR / fname
#     if not path.exists():
#         continue

#     try:
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#     except Exception:
#         continue

#     parsed = safe_json_load(data.get("output", ""))

#     if not parsed:
#         continue

#     for it in parsed:
#         if not isinstance(it, dict):
#             continue

#         sent = it.get("sentence")
#         asp = it.get("aspect")

#         if not sent or not asp:
#             continue

#         asp_norm = str(asp).lower().strip()
#         asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

#         rows.append({
#             "run": fname,
#             "sentence_norm": " ".join(str(sent).split()),
#             "canonical_aspect": asp_map,
#             "aspect_category": str(it.get("aspect_category")).lower().strip(),
#             "sentiment": str(it.get("sentiment")).lower().strip(),
#             "tone": str(it.get("tone")).lower().strip(),
#         })

#     progress.progress(i / max(len(all_log_files), 1))

# if not rows:
#     st.error("❌ No ABSA data recovered from logs.")
#     st.stop()

# raw_df = pd.DataFrame(rows)

# # =====================================================
# # AGGREGATE BY SENTENCE × ASPECT
# # =====================================================

# combined = []

# for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):

#     combined.append({
#         "sentence_norm": sent,
#         "canonical_aspect": asp,
#         "majority_category": g["aspect_category"].mode().iloc[0],
#         "majority_sentiment": g["sentiment"].mode().iloc[0],
#         "majority_tone": g["tone"].mode().iloc[0],
#     })

# pred_df = pd.DataFrame(combined)

# # =====================================================
# # LOAD GROUND TRUTH (AUTO-DETECT FORMAT)
# # =====================================================

# gt_df = pd.read_csv(GT_PATH)
# gt_df = gt_df.loc[:, ~gt_df.columns.str.contains("^Unnamed")]

# columns = set(gt_df.columns)

# MINIMAL_REQUIRED = {
#     "sentence",
#     "canonical_aspect",
#     "aspect_categories",
#     "sentiments",
#     "tones",
# }

# EXTENDED_REQUIRED = {
#     "sentence",
#     "canonical_aspect",
#     "raw_aspects",
#     "aspect_categories",
#     "sentiments",
#     "tones",
# }

# if MINIMAL_REQUIRED.issubset(columns):
#     st.info("📄 Minimal Ground Truth Format Detected")

# elif EXTENDED_REQUIRED.issubset(columns):
#     st.info("📊 Extended Ground Truth Format Detected")

#     CATEGORY_MAP = {
#         "e": "environment",
#         "s": "social",
#         "g": "governance"
#     }

#     gt_df["aspect_categories"] = (
#         gt_df["aspect_categories"]
#         .astype(str)
#         .str.lower()
#         .str.strip()
#         .map(lambda x: CATEGORY_MAP.get(x, x))
#     )

# else:
#     st.error("❌ Ground truth format not recognized.")
#     st.stop()

# # Normalize
# gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()
# gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
# gt_df["aspect_categories"] = gt_df["aspect_categories"].astype(str).str.lower().str.strip()
# gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
# gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()

# gt_df = gt_df.drop_duplicates(["sentence_norm", "canonical_aspect"])

# # =====================================================
# # ASPECT DETECTION METRICS
# # =====================================================

# gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
# pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

# tp_pairs = gt_pairs & pred_pairs
# fp_pairs = pred_pairs - gt_pairs
# fn_pairs = gt_pairs - pred_pairs

# P = len(tp_pairs) / (len(tp_pairs) + len(fp_pairs) + 1e-9)
# R = len(tp_pairs) / (len(tp_pairs) + len(fn_pairs) + 1e-9)
# F1 = 2 * P * R / (P + R + 1e-9)

# st.subheader("✅ Aspect Detection Performance")

# c1, c2, c3, c4 = st.columns(4)
# c1.metric("TP", len(tp_pairs))
# c2.metric("FP", len(fp_pairs))
# c3.metric("FN", len(fn_pairs))
# c4.metric("F1", f"{F1:.3f}")

# st.write(f"**Precision:** {P:.3f}")
# st.write(f"**Recall:** {R:.3f}")

# # =====================================================
# # LABEL EVALUATION
# # =====================================================

# eval_df = pd.merge(
#     gt_df,
#     pred_df,
#     on=["sentence_norm", "canonical_aspect"],
#     how="inner"
# )

# def accuracy(gt, pred):
#     return (gt == pred).mean()

# st.subheader("🏷 Aspect Category Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['aspect_categories'], eval_df['majority_category']):.3f}")

# st.subheader("😊 Sentiment Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['sentiments'], eval_df['majority_sentiment']):.3f}")

# st.subheader("🎯 Tone Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['tones'], eval_df['majority_tone']):.3f}")

# # =====================================================
# # DOWNLOADS
# # =====================================================

# with st.expander("📥 Download Evaluation Tables"):
#     st.download_button(
#         "Download Matched Samples",
#         eval_df.to_csv(index=False).encode("utf-8"),
#         "absa_eval_matched.csv",
#         mime="text/csv",
#     )


# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

# st.markdown("""
# This page evaluates **all ABSA experiment outputs** against the
# official **ground truth mapping CSV** and reports:

# - ✅ Aspect Detection Precision / Recall / F1
# - 🏷 Aspect Category Accuracy
# - 😊 Sentiment Accuracy
# - 🎯 Tone Accuracy
# - ❌ Detailed False Positives & False Negatives
# - 📥 Downloadable evaluation tables
# """)

# # =====================================================
# # DEPLOYMENT-SAFE PATH DISCOVERY
# # =====================================================

# def find_repo_root(start: Path) -> Path:
#     start = start.resolve()
#     for parent in [start] + list(start.parents):
#         if (parent / "logs").exists() or (parent / "data").exists():
#             return parent
#     return start

# PROJECT_ROOT = find_repo_root(Path.cwd())

# LOGS_DIR = PROJECT_ROOT / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"
# MAPPING_PATH = PROJECT_ROOT / "data" / "aspect_mapping.json"
# GT_PATH = PROJECT_ROOT / "data" / "ground_truth" / "absa_mapping.csv"

# # =====================================================
# # VALIDATE FILES
# # =====================================================

# missing = []
# for p in [REGISTRY_PATH, MAPPING_PATH, GT_PATH]:
#     if not p.exists():
#         missing.append(str(p))

# if missing:
#     st.error("❌ Missing required files:")
#     for m in missing:
#         st.code(m)
#     st.stop()

# # =====================================================
# # ROBUST JSON RECOVERY
# # =====================================================

# def recover_json_objects(text):
#     objects, buf, depth, in_obj = [], "", 0, False
#     for ch in text:
#         if ch == "{":
#             depth += 1
#             in_obj = True
#         if in_obj:
#             buf += ch
#         if ch == "}":
#             depth -= 1
#             if depth == 0 and buf:
#                 try:
#                     objects.append(json.loads(buf))
#                 except Exception:
#                     pass
#                 buf, in_obj = "", False
#     return objects


# def extract_json_arrays(text):
#     arrays, stack, start = [], [], None
#     for i, ch in enumerate(text):
#         if ch == "[":
#             if not stack:
#                 start = i
#             stack.append(ch)
#         elif ch == "]" and stack:
#             stack.pop()
#             if not stack and start is not None:
#                 arrays.append(text[start:i+1])
#                 start = None
#     return arrays


# def safe_json_load(text):
#     for arr in reversed(extract_json_arrays(text)):
#         try:
#             return json.loads(arr)
#         except Exception:
#             continue
#     return recover_json_objects(text)

# # =====================================================
# # LOAD ASPECT MAPPING
# # =====================================================

# with open(MAPPING_PATH, "r", encoding="utf-8") as f:
#     mapping_cfg = json.load(f)

# ASPECT_MAP = {}
# for group in mapping_cfg.get("mappings", []):
#     canonical = group["canonical"].lower().strip()
#     for alias in group["aliases"]:
#         ASPECT_MAP[alias.lower().strip()] = canonical

# # =====================================================
# # LOAD REGISTRY
# # =====================================================

# with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#     registry = json.load(f)

# sets = registry.get("sets", {})
# if not sets:
#     st.warning("⚠️ Registry contains no experiment sets.")
#     st.stop()

# # =====================================================
# # COLLECT LOG FILES
# # =====================================================

# all_log_files = set()
# file_to_sets = {}

# for set_name, files in sets.items():
#     for f in files:
#         all_log_files.add(f)
#         file_to_sets.setdefault(f, []).append(set_name)

# st.sidebar.metric("Experiment Sets", len(sets))
# st.sidebar.metric("Total Runs", len(all_log_files))

# # =====================================================
# # LOAD & NORMALIZE ALL RUNS
# # =====================================================

# rows = []
# progress = st.progress(0.0)

# for i, fname in enumerate(sorted(all_log_files), start=1):

#     path = LOGS_DIR / fname
#     if not path.exists():
#         continue

#     try:
#         with open(path, "r", encoding="utf-8") as f:
#             data = json.load(f)
#     except Exception:
#         continue

#     parsed = safe_json_load(data.get("output", ""))

#     if not parsed:
#         continue

#     for it in parsed:
#         if not isinstance(it, dict):
#             continue

#         sent = it.get("sentence")
#         asp = it.get("aspect")

#         if not sent or not asp:
#             continue

#         asp_norm = str(asp).lower().strip()
#         asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

#         rows.append({
#             "run": fname,
#             "experiment_sets": ", ".join(sorted(file_to_sets.get(fname, []))),

#             "sentence": sent,
#             "sentence_norm": " ".join(str(sent).split()),

#             "aspect_raw": asp,
#             "aspect_norm": asp_norm,
#             "canonical_aspect": asp_map,

#             "aspect_category": str(it.get("aspect_category")).lower().strip(),
#             "sentiment": str(it.get("sentiment")).lower().strip(),
#             "tone": str(it.get("tone")).lower().strip(),
#         })

#     progress.progress(i / max(len(all_log_files), 1))

# if not rows:
#     st.error("❌ No ABSA data recovered from logs.")
#     st.stop()

# raw_df = pd.DataFrame(rows)

# # =====================================================
# # AGGREGATE BY SENTENCE × ASPECT
# # =====================================================

# combined = []

# for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):

#     cats = g["aspect_category"].dropna().tolist()
#     sents = g["sentiment"].dropna().tolist()
#     tones = g["tone"].dropna().tolist()

#     combined.append({
#         "sentence_norm": sent,
#         "canonical_aspect": asp,

#         "majority_category": pd.Series(cats).mode().iloc[0] if cats else None,
#         "majority_sentiment": pd.Series(sents).mode().iloc[0] if sents else None,
#         "majority_tone": pd.Series(tones).mode().iloc[0] if tones else None,

#         "runs_count": g["run"].nunique(),
#     })

# pred_df = pd.DataFrame(combined)

# # =====================================================
# # LOAD GROUND TRUTH CSV (STRICT STRUCTURE)
# # =====================================================

# gt_df = pd.read_csv(GT_PATH)

# # Auto-clean accidental unnamed columns
# gt_df = gt_df.loc[:, ~gt_df.columns.str.contains("^Unnamed")]

# REQUIRED_COLS = [
#     "sentence",
#     "canonical_aspect",
#     "aspect_categories",
#     "sentiments",
#     "tones",
# ]

# missing_cols = set(REQUIRED_COLS) - set(gt_df.columns)
# if missing_cols:
#     st.error(f"❌ Ground truth CSV missing columns: {missing_cols}")
#     st.stop()

# # Normalize
# gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()
# gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
# gt_df["aspect_categories"] = gt_df["aspect_categories"].astype(str).str.lower().str.strip()
# gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
# gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()

# # =====================================================
# # ASPECT DETECTION METRICS
# # =====================================================

# gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
# pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

# tp_pairs = gt_pairs & pred_pairs
# fp_pairs = pred_pairs - gt_pairs
# fn_pairs = gt_pairs - pred_pairs

# P = len(tp_pairs) / (len(tp_pairs) + len(fp_pairs) + 1e-9)
# R = len(tp_pairs) / (len(tp_pairs) + len(fn_pairs) + 1e-9)
# F1 = 2 * P * R / (P + R + 1e-9)

# st.subheader("✅ Aspect Detection Performance")

# c1, c2, c3, c4 = st.columns(4)
# c1.metric("TP", len(tp_pairs))
# c2.metric("FP", len(fp_pairs))
# c3.metric("FN", len(fn_pairs))
# c4.metric("F1", f"{F1:.3f}")

# st.write(f"**Precision:** {P:.3f}")
# st.write(f"**Recall:** {R:.3f}")

# # =====================================================
# # MERGE FOR LABEL EVALUATION
# # =====================================================

# eval_df = pd.merge(
#     gt_df,
#     pred_df,
#     on=["sentence_norm", "canonical_aspect"],
#     how="inner"
# )

# st.subheader("🔗 Matched Aspect Pairs")
# st.caption(f"{len(eval_df)} matched samples")

# # =====================================================
# # CLASSIFICATION METRICS
# # =====================================================

# def accuracy(gt, pred):
#     return (gt == pred).mean()

# st.subheader("🏷 Aspect Category Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['aspect_categories'], eval_df['majority_category']):.3f}")

# st.subheader("😊 Sentiment Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['sentiments'], eval_df['majority_sentiment']):.3f}")

# st.subheader("🎯 Tone Accuracy")
# st.metric("Accuracy", f"{accuracy(eval_df['tones'], eval_df['majority_tone']):.3f}")

# # =====================================================
# # LABEL MISMATCH TABLE
# # =====================================================

# st.subheader("🔍 Label Mismatches")

# label_errors = eval_df[
#     (eval_df["aspect_categories"] != eval_df["majority_category"]) |
#     (eval_df["sentiments"] != eval_df["majority_sentiment"]) |
#     (eval_df["tones"] != eval_df["majority_tone"])
# ]

# st.dataframe(
#     label_errors[
#         [
#             "sentence_norm",
#             "canonical_aspect",
#             "aspect_categories", "majority_category",
#             "sentiments", "majority_sentiment",
#             "tones", "majority_tone",
#         ]
#     ],
#     use_container_width=True
# )

# # =====================================================
# # DOWNLOADS
# # =====================================================

# with st.expander("📥 Download Evaluation Tables"):

#     st.download_button(
#         "Download Matched Samples",
#         eval_df.to_csv(index=False).encode("utf-8"),
#         "absa_eval_matched.csv",
#         mime="text/csv",
#     )

#     st.download_button(
#         "Download Aggregated Predictions",
#         pred_df.to_csv(index=False).encode("utf-8"),
#         "absa_predictions_aggregated.csv",
#         mime="text/csv",
#     )



# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# LOGS_DIR = BASE_DIR / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"
# MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"
# GT_PATH = BASE_DIR / "data" / "ground_truth" / "absa_mapping.csv"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

# st.markdown("""
# This page evaluates **all ABSA experiment outputs** against the
# official **ground truth mapping CSV** and reports:

# - ✅ Aspect Detection Precision / Recall / F1
# - 🏷 Aspect Category Accuracy
# - 😊 Sentiment Accuracy
# - 🎯 Tone Accuracy
# - ❌ Detailed False Positives & False Negatives
# - 📥 Downloadable evaluation tables
# """)

# # =====================================================
# # UTIL — ROBUST JSON RECOVERY
# # =====================================================

# def recover_json_objects(text):
#     objects, buf, depth, in_obj = [], "", 0, False
#     for ch in text:
#         if ch == "{":
#             depth += 1
#             in_obj = True
#         if in_obj:
#             buf += ch
#         if ch == "}":
#             depth -= 1
#             if depth == 0 and buf:
#                 try:
#                     objects.append(json.loads(buf))
#                 except Exception:
#                     pass
#                 buf, in_obj = "", False
#     return objects


# def extract_json_arrays(text):
#     arrays, stack, start = [], [], None
#     for i, ch in enumerate(text):
#         if ch == "[":
#             if not stack:
#                 start = i
#             stack.append(ch)
#         elif ch == "]" and stack:
#             stack.pop()
#             if not stack and start is not None:
#                 arrays.append(text[start:i+1])
#                 start = None
#     return arrays


# def safe_json_load(text):
#     for arr in reversed(extract_json_arrays(text)):
#         try:
#             return json.loads(arr)
#         except Exception:
#             continue
#     return recover_json_objects(text)

# # =====================================================
# # LOAD ASPECT MAPPING
# # =====================================================

# if not MAPPING_PATH.exists():
#     st.error("❌ data/aspect_mapping.json not found.")
#     st.stop()

# with open(MAPPING_PATH, "r", encoding="utf-8") as f:
#     mapping_cfg = json.load(f)

# ASPECT_MAP = {}
# for group in mapping_cfg.get("mappings", []):
#     canonical = group["canonical"].lower().strip()
#     for alias in group["aliases"]:
#         ASPECT_MAP[alias.lower().strip()] = canonical

# # =====================================================
# # LOAD REGISTRY (ALL SETS)
# # =====================================================

# if not REGISTRY_PATH.exists():
#     st.error("❌ registry.json not found.")
#     st.stop()

# with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#     registry = json.load(f)

# sets = registry.get("sets", {})
# if not sets:
#     st.error("❌ No experiment sets found.")
#     st.stop()

# # =====================================================
# # COLLECT ALL UNIQUE LOG FILES
# # =====================================================

# all_log_files = set()
# file_to_sets = {}

# for set_name, files in sets.items():
#     for f in files:
#         all_log_files.add(f)
#         file_to_sets.setdefault(f, []).append(set_name)

# st.sidebar.metric("Experiment Sets", len(sets))
# st.sidebar.metric("Total Runs", len(all_log_files))

# # =====================================================
# # LOAD & NORMALIZE ALL RUNS
# # =====================================================

# rows = []
# progress = st.progress(0.0)

# for i, fname in enumerate(sorted(all_log_files), start=1):

#     path = LOGS_DIR / fname
#     if not path.exists():
#         continue

#     with open(path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     parsed = safe_json_load(data.get("output", ""))

#     if not parsed:
#         continue

#     for it in parsed:
#         if not isinstance(it, dict):
#             continue

#         sent = it.get("sentence")
#         asp = it.get("aspect")

#         if not sent or not asp:
#             continue

#         asp_norm = str(asp).lower().strip()
#         asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

#         rows.append({
#             "run": fname,
#             "experiment_sets": ", ".join(sorted(file_to_sets.get(fname, []))),

#             "sentence": sent,
#             "sentence_norm": " ".join(str(sent).split()),

#             "aspect_raw": asp,
#             "aspect_norm": asp_norm,
#             "canonical_aspect": asp_map,

#             "aspect_category": str(it.get("aspect_category")).lower().strip(),
#             "sentiment": str(it.get("sentiment")).lower().strip(),
#             "tone": str(it.get("tone")).lower().strip(),
#             "confidence": it.get("confidence"),
#         })

#     progress.progress(i / len(all_log_files))

# if not rows:
#     st.error("No ABSA data recovered from logs.")
#     st.stop()

# raw_df = pd.DataFrame(rows)

# # =====================================================
# # AGGREGATE BY SENTENCE × ASPECT
# # =====================================================

# combined = []

# for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):

#     cats = g["aspect_category"].dropna().tolist()
#     sents = g["sentiment"].dropna().tolist()
#     tones = g["tone"].dropna().tolist()

#     combined.append({
#         "sentence_norm": sent,
#         "canonical_aspect": asp,

#         "majority_category": pd.Series(cats).mode().iloc[0] if cats else None,
#         "majority_sentiment": pd.Series(sents).mode().iloc[0] if sents else None,
#         "majority_tone": pd.Series(tones).mode().iloc[0] if tones else None,

#         "runs_count": g["run"].nunique(),
#     })

# pred_df = pd.DataFrame(combined)

# # =====================================================
# # LOAD GROUND TRUTH
# # =====================================================

# if not GT_PATH.exists():
#     st.error("❌ Ground truth not found: data/ground_truth/absa_mapping.csv")
#     st.stop()

# gt_df = pd.read_csv(GT_PATH)

# REQUIRED_COLS = {
#     "sentence",
#     "canonical_aspect",
#     "aspect_categories",
#     "sentiments",
#     "tones",
# }

# if not REQUIRED_COLS.issubset(gt_df.columns):
#     st.error(f"Ground truth must contain columns: {REQUIRED_COLS}")
#     st.stop()

# gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()
# gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
# gt_df["aspect_categories"] = gt_df["aspect_categories"].astype(str).str.lower().str.strip()
# gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
# gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()

# # =====================================================
# # ASPECT DETECTION METRICS
# # =====================================================

# gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
# pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

# tp_pairs = gt_pairs & pred_pairs
# fp_pairs = pred_pairs - gt_pairs
# fn_pairs = gt_pairs - pred_pairs

# P = len(tp_pairs) / (len(tp_pairs) + len(fp_pairs) + 1e-9)
# R = len(tp_pairs) / (len(tp_pairs) + len(fn_pairs) + 1e-9)
# F1 = 2 * P * R / (P + R + 1e-9)

# st.subheader("✅ Aspect Detection Performance")

# c1, c2, c3, c4 = st.columns(4)
# c1.metric("TP", len(tp_pairs))
# c2.metric("FP", len(fp_pairs))
# c3.metric("FN", len(fn_pairs))
# c4.metric("F1", f"{F1:.3f}")

# st.write(f"**Precision:** {P:.3f}")
# st.write(f"**Recall:** {R:.3f}")

# # =====================================================
# # DETAILED SET DIFFERENCE TABLES
# # =====================================================

# pred_keys = pred_df[["sentence_norm", "canonical_aspect"]].apply(tuple, axis=1)
# gt_keys = gt_df[["sentence_norm", "canonical_aspect"]].apply(tuple, axis=1)

# pred_not_in_gt = pred_df[~pred_keys.isin(gt_keys)].copy()
# gt_not_in_pred = gt_df[~gt_keys.isin(pred_keys)].copy()

# st.subheader("❌ Predicted Aspects NOT in Ground Truth (Detailed False Positives)")
# st.caption(f"{len(pred_not_in_gt)} predicted aspects not found in ground truth")

# st.dataframe(
#     pred_not_in_gt[
#         [
#             "sentence_norm",
#             "canonical_aspect",
#             "majority_category",
#             "majority_sentiment",
#             "majority_tone",
#             "runs_count",
#         ]
#     ],
#     use_container_width=True,
# )

# st.subheader("❌ Ground Truth Aspects MISSED by Model (Detailed False Negatives)")
# st.caption(f"{len(gt_not_in_pred)} ground truth aspects not detected by model")

# st.dataframe(
#     gt_not_in_pred[
#         [
#             "sentence_norm",
#             "canonical_aspect",
#             "aspect_categories",
#             "sentiments",
#             "tones",
#         ]
#     ],
#     use_container_width=True,
# )

# # =====================================================
# # MERGE FOR LABEL EVALUATION
# # =====================================================

# eval_df = pd.merge(
#     gt_df,
#     pred_df,
#     on=["sentence_norm", "canonical_aspect"],
#     how="inner"
# )

# st.subheader("🔗 Matched Aspect Pairs for Label Evaluation")
# st.caption(f"{len(eval_df)} matched samples")

# # =====================================================
# # CLASSIFICATION METRICS
# # =====================================================

# def cls_metrics(gt, pred):
#     tp = (gt == pred).sum()
#     fp = (gt != pred).sum()
#     precision = tp / (tp + fp + 1e-9)
#     recall = tp / (tp + 1e-9)
#     f1 = 2 * precision * recall / (precision + recall + 1e-9)
#     return tp, fp, precision, recall, f1


# st.subheader("🏷 Aspect Category Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["aspect_categories"],
#     eval_df["majority_category"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


# st.subheader("😊 Sentiment Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["sentiments"],
#     eval_df["majority_sentiment"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


# st.subheader("🎯 Tone Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["tones"],
#     eval_df["majority_tone"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")

# # =====================================================
# # LABEL MISMATCH TABLE
# # =====================================================

# st.subheader("🔍 Label Mismatches (Matched Aspects)")

# label_errors = eval_df[
#     (eval_df["aspect_categories"] != eval_df["majority_category"]) |
#     (eval_df["sentiments"] != eval_df["majority_sentiment"]) |
#     (eval_df["tones"] != eval_df["majority_tone"])
# ]

# st.dataframe(
#     label_errors[
#         [
#             "sentence_norm",
#             "canonical_aspect",
#             "aspect_categories", "majority_category",
#             "sentiments", "majority_sentiment",
#             "tones", "majority_tone",
#         ]
#     ],
#     use_container_width=True
# )

# # =====================================================
# # DOWNLOAD TABLES
# # =====================================================

# with st.expander("📥 Download Evaluation Tables"):

#     st.download_button(
#         "Download Matched Eval Samples",
#         eval_df.to_csv(index=False).encode("utf-8"),
#         "absa_eval_matched.csv",
#         mime="text/csv",
#     )

#     st.download_button(
#         "Download Prediction Table (Aggregated)",
#         pred_df.to_csv(index=False).encode("utf-8"),
#         "absa_predictions_aggregated.csv",
#         mime="text/csv",
#     )

#     st.download_button(
#         "Download Predicted Not in Ground Truth (False Positives)",
#         pred_not_in_gt.to_csv(index=False).encode("utf-8"),
#         "absa_false_positives_detailed.csv",
#         mime="text/csv",
#     )

#     st.download_button(
#         "Download Ground Truth Missed by Model (False Negatives)",
#         gt_not_in_pred.to_csv(index=False).encode("utf-8"),
#         "absa_false_negatives_detailed.csv",
#         mime="text/csv",
#     )


# import streamlit as st
# from pathlib import Path
# import json
# import pandas as pd

# # =====================================================
# # PATH SETUP
# # =====================================================

# BASE_DIR = Path(__file__).resolve().parents[1]
# LOGS_DIR = BASE_DIR / "logs"
# REGISTRY_PATH = LOGS_DIR / "registry.json"
# MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"
# GT_PATH = BASE_DIR / "data" / "ground_truth" / "absa_mapping.csv"

# # =====================================================
# # PAGE CONFIG
# # =====================================================

# st.set_page_config(layout="wide")
# st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

# st.markdown("""
# This page evaluates **all ABSA experiment outputs** against the
# official **ground truth mapping CSV** and reports:

# - Aspect Detection Precision / Recall / F1
# - Aspect Category Accuracy
# - Sentiment Accuracy
# - Tone Accuracy
# - Detailed error analysis
# """)

# # =====================================================
# # UTIL — ROBUST JSON RECOVERY
# # =====================================================

# def recover_json_objects(text):
#     objects, buf, depth, in_obj = [], "", 0, False
#     for ch in text:
#         if ch == "{":
#             depth += 1
#             in_obj = True
#         if in_obj:
#             buf += ch
#         if ch == "}":
#             depth -= 1
#             if depth == 0 and buf:
#                 try:
#                     objects.append(json.loads(buf))
#                 except Exception:
#                     pass
#                 buf, in_obj = "", False
#     return objects


# def extract_json_arrays(text):
#     arrays, stack, start = [], [], None
#     for i, ch in enumerate(text):
#         if ch == "[":
#             if not stack:
#                 start = i
#             stack.append(ch)
#         elif ch == "]" and stack:
#             stack.pop()
#             if not stack and start is not None:
#                 arrays.append(text[start:i+1])
#                 start = None
#     return arrays


# def safe_json_load(text):
#     for arr in reversed(extract_json_arrays(text)):
#         try:
#             return json.loads(arr)
#         except Exception:
#             continue
#     return recover_json_objects(text)

# # =====================================================
# # LOAD ASPECT MAPPING
# # =====================================================

# if not MAPPING_PATH.exists():
#     st.error("❌ data/aspect_mapping.json not found.")
#     st.stop()

# with open(MAPPING_PATH, "r", encoding="utf-8") as f:
#     mapping_cfg = json.load(f)

# ASPECT_MAP = {}
# for group in mapping_cfg.get("mappings", []):
#     canonical = group["canonical"].lower().strip()
#     for alias in group["aliases"]:
#         ASPECT_MAP[alias.lower().strip()] = canonical

# # =====================================================
# # LOAD REGISTRY (ALL SETS)
# # =====================================================

# if not REGISTRY_PATH.exists():
#     st.error("❌ registry.json not found.")
#     st.stop()

# with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
#     registry = json.load(f)

# sets = registry.get("sets", {})
# if not sets:
#     st.error("❌ No experiment sets found.")
#     st.stop()

# # =====================================================
# # COLLECT ALL UNIQUE LOG FILES
# # =====================================================

# all_log_files = set()
# file_to_sets = {}

# for set_name, files in sets.items():
#     for f in files:
#         all_log_files.add(f)
#         file_to_sets.setdefault(f, []).append(set_name)

# st.sidebar.metric("Experiment Sets", len(sets))
# st.sidebar.metric("Total Runs", len(all_log_files))

# # =====================================================
# # LOAD & NORMALIZE ALL RUNS
# # =====================================================

# rows = []
# progress = st.progress(0.0)

# for i, fname in enumerate(sorted(all_log_files), start=1):

#     path = LOGS_DIR / fname
#     if not path.exists():
#         continue

#     with open(path, "r", encoding="utf-8") as f:
#         data = json.load(f)

#     parsed = safe_json_load(data.get("output", ""))

#     if not parsed:
#         continue

#     for it in parsed:
#         if not isinstance(it, dict):
#             continue

#         sent = it.get("sentence")
#         asp = it.get("aspect")

#         if not sent or not asp:
#             continue

#         asp_norm = str(asp).lower().strip()
#         asp_map = ASPECT_MAP.get(asp_norm, asp_norm)

#         rows.append({
#             "run": fname,
#             "experiment_sets": ", ".join(sorted(file_to_sets.get(fname, []))),

#             "sentence": sent,
#             "sentence_norm": " ".join(str(sent).split()),

#             "aspect_raw": asp,
#             "aspect_norm": asp_norm,
#             "canonical_aspect": asp_map,

#             "aspect_category": str(it.get("aspect_category")).lower().strip(),
#             "sentiment": str(it.get("sentiment")).lower().strip(),
#             "tone": str(it.get("tone")).lower().strip(),
#             "confidence": it.get("confidence"),
#         })

#     progress.progress(i / len(all_log_files))

# if not rows:
#     st.error("No ABSA data recovered from logs.")
#     st.stop()

# raw_df = pd.DataFrame(rows)

# # =====================================================
# # AGGREGATE BY SENTENCE × ASPECT
# # =====================================================

# combined = []

# for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):

#     cats = g["aspect_category"].dropna().tolist()
#     sents = g["sentiment"].dropna().tolist()
#     tones = g["tone"].dropna().tolist()

#     combined.append({
#         "sentence_norm": sent,
#         "canonical_aspect": asp,

#         "majority_category": pd.Series(cats).mode().iloc[0] if cats else None,
#         "majority_sentiment": pd.Series(sents).mode().iloc[0] if sents else None,
#         "majority_tone": pd.Series(tones).mode().iloc[0] if tones else None,

#         "runs_count": g["run"].nunique(),
#     })

# pred_df = pd.DataFrame(combined)

# # =====================================================
# # LOAD GROUND TRUTH
# # =====================================================

# if not GT_PATH.exists():
#     st.error("❌ Ground truth not found: data/ground_truth/absa_mapping.csv")
#     st.stop()

# gt_df = pd.read_csv(GT_PATH)

# REQUIRED_COLS = {
#     "sentence",
#     "canonical_aspect",
#     "aspect_categories",
#     "sentiments",
#     "tones",
# }

# if not REQUIRED_COLS.issubset(gt_df.columns):
#     st.error(f"Ground truth must contain columns: {REQUIRED_COLS}")
#     st.stop()

# gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()
# gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
# gt_df["aspect_categories"] = gt_df["aspect_categories"].astype(str).str.lower().str.strip()
# gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
# gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()

# # =====================================================
# # ASPECT DETECTION METRICS
# # =====================================================

# gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
# pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

# tp_pairs = gt_pairs & pred_pairs
# fp_pairs = pred_pairs - gt_pairs
# fn_pairs = gt_pairs - pred_pairs

# P = len(tp_pairs) / (len(tp_pairs) + len(fp_pairs) + 1e-9)
# R = len(tp_pairs) / (len(tp_pairs) + len(fn_pairs) + 1e-9)
# F1 = 2 * P * R / (P + R + 1e-9)

# st.subheader("✅ Aspect Detection Performance")

# c1, c2, c3, c4 = st.columns(4)
# c1.metric("TP", len(tp_pairs))
# c2.metric("FP", len(fp_pairs))
# c3.metric("FN", len(fn_pairs))
# c4.metric("F1", f"{F1:.3f}")

# st.write(f"**Precision:** {P:.3f}")
# st.write(f"**Recall:** {R:.3f}")

# # =====================================================
# # MERGE FOR LABEL EVALUATION
# # =====================================================

# eval_df = pd.merge(
#     gt_df,
#     pred_df,
#     on=["sentence_norm", "canonical_aspect"],
#     how="inner"
# )

# st.subheader("🔗 Matched Aspect Pairs for Label Evaluation")
# st.caption(f"{len(eval_df)} matched samples")

# # =====================================================
# # CLASSIFICATION METRICS
# # =====================================================

# def cls_metrics(gt, pred):
#     tp = (gt == pred).sum()
#     fp = (gt != pred).sum()
#     precision = tp / (tp + fp + 1e-9)
#     recall = tp / (tp + 1e-9)
#     f1 = 2 * precision * recall / (precision + recall + 1e-9)
#     return tp, fp, precision, recall, f1


# st.subheader("🏷 Aspect Category Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["aspect_categories"],
#     eval_df["majority_category"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


# st.subheader("😊 Sentiment Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["sentiments"],
#     eval_df["majority_sentiment"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


# st.subheader("🎯 Tone Classification")

# tp, fp, p, r, f1 = cls_metrics(
#     eval_df["tones"],
#     eval_df["majority_tone"]
# )

# st.write(f"TP: {tp} | FP: {fp}")
# st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")

# # =====================================================
# # ERROR ANALYSIS
# # =====================================================

# st.subheader("❌ Missing Aspects (False Negatives)")

# fn_df = pd.DataFrame(list(fn_pairs), columns=["sentence_norm", "canonical_aspect"])
# st.dataframe(fn_df, use_container_width=True)


# st.subheader("⚠️ Spurious Aspects (False Positives)")

# fp_df = pd.DataFrame(list(fp_pairs), columns=["sentence_norm", "canonical_aspect"])
# st.dataframe(fp_df, use_container_width=True)


# st.subheader("🔍 Label Mismatches")

# label_errors = eval_df[
#     (eval_df["aspect_categories"] != eval_df["majority_category"]) |
#     (eval_df["sentiments"] != eval_df["majority_sentiment"]) |
#     (eval_df["tones"] != eval_df["majority_tone"])
# ]

# st.dataframe(
#     label_errors[
#         [
#             "sentence_norm",
#             "canonical_aspect",
#             "aspect_categories", "majority_category",
#             "sentiments", "majority_sentiment",
#             "tones", "majority_tone",
#         ]
#     ],
#     use_container_width=True
# )

# # =====================================================
# # DOWNLOAD EVAL TABLE
# # =====================================================

# with st.expander("📥 Download Evaluation Tables"):

#     st.download_button(
#         "Download Matched Eval Samples",
#         eval_df.to_csv(index=False).encode("utf-8"),
#         "absa_eval_matched.csv",
#         mime="text/csv",
#     )

#     st.download_button(
#         "Download Prediction Table",
#         pred_df.to_csv(index=False).encode("utf-8"),
#         "absa_predictions_aggregated.csv",
#         mime="text/csv",
#     )
