import streamlit as st
from pathlib import Path
import json
import pandas as pd

# =====================================================
# PATH SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]
LOGS_DIR = BASE_DIR / "logs"
REGISTRY_PATH = LOGS_DIR / "registry.json"
MAPPING_PATH = BASE_DIR / "data" / "aspect_mapping.json"
GT_PATH = BASE_DIR / "data" / "ground_truth" / "absa_mapping.csv"

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(layout="wide")
st.title("🧪 ABSA Ground Truth Evaluation Dashboard")

st.markdown("""
This page evaluates **all ABSA experiment outputs** against the
official **ground truth mapping CSV** and reports:

- ✅ Aspect Detection Precision / Recall / F1
- 🏷 Aspect Category Accuracy
- 😊 Sentiment Accuracy
- 🎯 Tone Accuracy
- ❌ Detailed False Positives & False Negatives
- 📥 Downloadable evaluation tables
""")

# =====================================================
# UTIL — ROBUST JSON RECOVERY
# =====================================================

def recover_json_objects(text):
    objects, buf, depth, in_obj = [], "", 0, False
    for ch in text:
        if ch == "{":
            depth += 1
            in_obj = True
        if in_obj:
            buf += ch
        if ch == "}":
            depth -= 1
            if depth == 0 and buf:
                try:
                    objects.append(json.loads(buf))
                except Exception:
                    pass
                buf, in_obj = "", False
    return objects


def extract_json_arrays(text):
    arrays, stack, start = [], [], None
    for i, ch in enumerate(text):
        if ch == "[":
            if not stack:
                start = i
            stack.append(ch)
        elif ch == "]" and stack:
            stack.pop()
            if not stack and start is not None:
                arrays.append(text[start:i+1])
                start = None
    return arrays


def safe_json_load(text):
    for arr in reversed(extract_json_arrays(text)):
        try:
            return json.loads(arr)
        except Exception:
            continue
    return recover_json_objects(text)

# =====================================================
# LOAD ASPECT MAPPING
# =====================================================

if not MAPPING_PATH.exists():
    st.error("❌ data/aspect_mapping.json not found.")
    st.stop()

with open(MAPPING_PATH, "r", encoding="utf-8") as f:
    mapping_cfg = json.load(f)

ASPECT_MAP = {}
for group in mapping_cfg.get("mappings", []):
    canonical = group["canonical"].lower().strip()
    for alias in group["aliases"]:
        ASPECT_MAP[alias.lower().strip()] = canonical

# =====================================================
# LOAD REGISTRY (ALL SETS)
# =====================================================

if not REGISTRY_PATH.exists():
    st.error("❌ registry.json not found.")
    st.stop()

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    registry = json.load(f)

sets = registry.get("sets", {})
if not sets:
    st.error("❌ No experiment sets found.")
    st.stop()

# =====================================================
# COLLECT ALL UNIQUE LOG FILES
# =====================================================

all_log_files = set()
file_to_sets = {}

for set_name, files in sets.items():
    for f in files:
        all_log_files.add(f)
        file_to_sets.setdefault(f, []).append(set_name)

st.sidebar.metric("Experiment Sets", len(sets))
st.sidebar.metric("Total Runs", len(all_log_files))

# =====================================================
# LOAD & NORMALIZE ALL RUNS
# =====================================================

rows = []
progress = st.progress(0.0)

for i, fname in enumerate(sorted(all_log_files), start=1):

    path = LOGS_DIR / fname
    if not path.exists():
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parsed = safe_json_load(data.get("output", ""))

    if not parsed:
        continue

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
            "run": fname,
            "experiment_sets": ", ".join(sorted(file_to_sets.get(fname, []))),

            "sentence": sent,
            "sentence_norm": " ".join(str(sent).split()),

            "aspect_raw": asp,
            "aspect_norm": asp_norm,
            "canonical_aspect": asp_map,

            "aspect_category": str(it.get("aspect_category")).lower().strip(),
            "sentiment": str(it.get("sentiment")).lower().strip(),
            "tone": str(it.get("tone")).lower().strip(),
            "confidence": it.get("confidence"),
        })

    progress.progress(i / len(all_log_files))

if not rows:
    st.error("No ABSA data recovered from logs.")
    st.stop()

raw_df = pd.DataFrame(rows)

# =====================================================
# AGGREGATE BY SENTENCE × ASPECT
# =====================================================

combined = []

for (sent, asp), g in raw_df.groupby(["sentence_norm", "canonical_aspect"]):

    cats = g["aspect_category"].dropna().tolist()
    sents = g["sentiment"].dropna().tolist()
    tones = g["tone"].dropna().tolist()

    combined.append({
        "sentence_norm": sent,
        "canonical_aspect": asp,

        "majority_category": pd.Series(cats).mode().iloc[0] if cats else None,
        "majority_sentiment": pd.Series(sents).mode().iloc[0] if sents else None,
        "majority_tone": pd.Series(tones).mode().iloc[0] if tones else None,

        "runs_count": g["run"].nunique(),
    })

pred_df = pd.DataFrame(combined)

# =====================================================
# LOAD GROUND TRUTH
# =====================================================

if not GT_PATH.exists():
    st.error("❌ Ground truth not found: data/ground_truth/absa_mapping.csv")
    st.stop()

gt_df = pd.read_csv(GT_PATH)

REQUIRED_COLS = {
    "sentence",
    "canonical_aspect",
    "aspect_categories",
    "sentiments",
    "tones",
}

if not REQUIRED_COLS.issubset(gt_df.columns):
    st.error(f"Ground truth must contain columns: {REQUIRED_COLS}")
    st.stop()

gt_df["sentence_norm"] = gt_df["sentence"].astype(str).str.strip()
gt_df["canonical_aspect"] = gt_df["canonical_aspect"].astype(str).str.lower().str.strip()
gt_df["aspect_categories"] = gt_df["aspect_categories"].astype(str).str.lower().str.strip()
gt_df["sentiments"] = gt_df["sentiments"].astype(str).str.lower().str.strip()
gt_df["tones"] = gt_df["tones"].astype(str).str.lower().str.strip()

# =====================================================
# ASPECT DETECTION METRICS
# =====================================================

gt_pairs = set(zip(gt_df["sentence_norm"], gt_df["canonical_aspect"]))
pred_pairs = set(zip(pred_df["sentence_norm"], pred_df["canonical_aspect"]))

tp_pairs = gt_pairs & pred_pairs
fp_pairs = pred_pairs - gt_pairs
fn_pairs = gt_pairs - pred_pairs

P = len(tp_pairs) / (len(tp_pairs) + len(fp_pairs) + 1e-9)
R = len(tp_pairs) / (len(tp_pairs) + len(fn_pairs) + 1e-9)
F1 = 2 * P * R / (P + R + 1e-9)

st.subheader("✅ Aspect Detection Performance")

c1, c2, c3, c4 = st.columns(4)
c1.metric("TP", len(tp_pairs))
c2.metric("FP", len(fp_pairs))
c3.metric("FN", len(fn_pairs))
c4.metric("F1", f"{F1:.3f}")

st.write(f"**Precision:** {P:.3f}")
st.write(f"**Recall:** {R:.3f}")

# =====================================================
# DETAILED SET DIFFERENCE TABLES
# =====================================================

pred_keys = pred_df[["sentence_norm", "canonical_aspect"]].apply(tuple, axis=1)
gt_keys = gt_df[["sentence_norm", "canonical_aspect"]].apply(tuple, axis=1)

pred_not_in_gt = pred_df[~pred_keys.isin(gt_keys)].copy()
gt_not_in_pred = gt_df[~gt_keys.isin(pred_keys)].copy()

st.subheader("❌ Predicted Aspects NOT in Ground Truth (Detailed False Positives)")
st.caption(f"{len(pred_not_in_gt)} predicted aspects not found in ground truth")

st.dataframe(
    pred_not_in_gt[
        [
            "sentence_norm",
            "canonical_aspect",
            "majority_category",
            "majority_sentiment",
            "majority_tone",
            "runs_count",
        ]
    ],
    use_container_width=True,
)

st.subheader("❌ Ground Truth Aspects MISSED by Model (Detailed False Negatives)")
st.caption(f"{len(gt_not_in_pred)} ground truth aspects not detected by model")

st.dataframe(
    gt_not_in_pred[
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

# =====================================================
# MERGE FOR LABEL EVALUATION
# =====================================================

eval_df = pd.merge(
    gt_df,
    pred_df,
    on=["sentence_norm", "canonical_aspect"],
    how="inner"
)

st.subheader("🔗 Matched Aspect Pairs for Label Evaluation")
st.caption(f"{len(eval_df)} matched samples")

# =====================================================
# CLASSIFICATION METRICS
# =====================================================

def cls_metrics(gt, pred):
    tp = (gt == pred).sum()
    fp = (gt != pred).sum()
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + 1e-9)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    return tp, fp, precision, recall, f1


st.subheader("🏷 Aspect Category Classification")

tp, fp, p, r, f1 = cls_metrics(
    eval_df["aspect_categories"],
    eval_df["majority_category"]
)

st.write(f"TP: {tp} | FP: {fp}")
st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


st.subheader("😊 Sentiment Classification")

tp, fp, p, r, f1 = cls_metrics(
    eval_df["sentiments"],
    eval_df["majority_sentiment"]
)

st.write(f"TP: {tp} | FP: {fp}")
st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")


st.subheader("🎯 Tone Classification")

tp, fp, p, r, f1 = cls_metrics(
    eval_df["tones"],
    eval_df["majority_tone"]
)

st.write(f"TP: {tp} | FP: {fp}")
st.write(f"Precision: {p:.3f} | Recall: {r:.3f} | F1: {f1:.3f}")

# =====================================================
# LABEL MISMATCH TABLE
# =====================================================

st.subheader("🔍 Label Mismatches (Matched Aspects)")

label_errors = eval_df[
    (eval_df["aspect_categories"] != eval_df["majority_category"]) |
    (eval_df["sentiments"] != eval_df["majority_sentiment"]) |
    (eval_df["tones"] != eval_df["majority_tone"])
]

st.dataframe(
    label_errors[
        [
            "sentence_norm",
            "canonical_aspect",
            "aspect_categories", "majority_category",
            "sentiments", "majority_sentiment",
            "tones", "majority_tone",
        ]
    ],
    use_container_width=True
)

# =====================================================
# DOWNLOAD TABLES
# =====================================================

with st.expander("📥 Download Evaluation Tables"):

    st.download_button(
        "Download Matched Eval Samples",
        eval_df.to_csv(index=False).encode("utf-8"),
        "absa_eval_matched.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download Prediction Table (Aggregated)",
        pred_df.to_csv(index=False).encode("utf-8"),
        "absa_predictions_aggregated.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download Predicted Not in Ground Truth (False Positives)",
        pred_not_in_gt.to_csv(index=False).encode("utf-8"),
        "absa_false_positives_detailed.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download Ground Truth Missed by Model (False Negatives)",
        gt_not_in_pred.to_csv(index=False).encode("utf-8"),
        "absa_false_negatives_detailed.csv",
        mime="text/csv",
    )


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
