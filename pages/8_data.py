import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")
st.title("📊 ABSA CSV Comparison & Consistency Analyzer")

st.markdown("""
Upload your ABSA CSV output and compare:
- Aspect labels
- ESG dimensions (E / S / G / ESG)
- Sentiment polarity
- Role / Type (Commitment, Action, Outcome, Policy, Concern)
Across different annotations or runs.
""")

# =====================================================
# UPLOAD CSV
# =====================================================

uploaded = st.file_uploader("📤 Upload ABSA CSV", type=["csv"])

if not uploaded:
    st.info("Please upload a CSV file to start.")
    st.stop()

df = pd.read_csv(uploaded)

st.subheader("📄 Raw Data Preview")
st.dataframe(df, use_container_width=True)

# =====================================================
# COLUMN MAPPING
# =====================================================

st.subheader("🧩 Column Mapping")

cols = df.columns.tolist()

sentence_col = st.selectbox("Sentence Column", cols, index=0)
aspect_col = st.selectbox("Aspect Column", cols, index=1)
esg_col = st.selectbox("ESG Dimension Column", cols, index=2)
sentiment_col = st.selectbox("Sentiment Column", cols, index=3)
role_col = st.selectbox("Role / Type Column", cols, index=4)

run_col = None
if len(cols) > 5:
    run_col = st.selectbox("Run/File Column (optional)", ["<none>"] + cols)
    if run_col == "<none>":
        run_col = None

# =====================================================
# NORMALIZATION
# =====================================================

df["sentence_norm"] = df[sentence_col].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
df["aspect_norm"] = df[aspect_col].astype(str).str.lower().str.strip()
df["esg_norm"] = df[esg_col].astype(str).str.upper().str.strip()
df["sentiment_norm"] = df[sentiment_col].astype(str).str.lower().str.strip()
df["role_norm"] = df[role_col].astype(str).str.lower().str.strip()

# =====================================================
# OVERALL DISTRIBUTIONS
# =====================================================

st.subheader("📊 Overall Distributions")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown("### 🏷 Aspect")
    st.bar_chart(df["aspect_norm"].value_counts())

with c2:
    st.markdown("### 🧭 ESG Dimension")
    st.bar_chart(df["esg_norm"].value_counts())

with c3:
    st.markdown("### 😊 Sentiment")
    st.bar_chart(df["sentiment_norm"].value_counts())

with c4:
    st.markdown("### 🎯 Role / Type")
    st.bar_chart(df["role_norm"].value_counts())

# =====================================================
# SENTENCE-LEVEL AGREEMENT
# =====================================================

st.subheader("🧬 Sentence-Level Consistency")

group = df.groupby("sentence_norm")

consistency = pd.DataFrame({
    "sentence": group.size().index,
    "unique_aspects": group["aspect_norm"].nunique().values,
    "unique_esg": group["esg_norm"].nunique().values,
    "unique_sentiment": group["sentiment_norm"].nunique().values,
    "unique_role": group["role_norm"].nunique().values,
    "annotations": group.size().values,
})

st.markdown("### 🔍 Disagreement Summary")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Aspect Disagreement", (consistency["unique_aspects"] > 1).sum())

with c2:
    st.metric("ESG Disagreement", (consistency["unique_esg"] > 1).sum())

with c3:
    st.metric("Sentiment Disagreement", (consistency["unique_sentiment"] > 1).sum())

with c4:
    st.metric("Role Disagreement", (consistency["unique_role"] > 1).sum())

st.markdown("### 📋 Sentences with Disagreement")

disagree_df = consistency[
    (consistency["unique_aspects"] > 1)
    | (consistency["unique_esg"] > 1)
    | (consistency["unique_sentiment"] > 1)
    | (consistency["unique_role"] > 1)
]

st.dataframe(disagree_df, use_container_width=True)

# =====================================================
# FOCUSED ASPECT ANALYSIS
# =====================================================

st.subheader("🎯 Focused Aspect Comparison")

aspect_list = sorted(df["aspect_norm"].unique())

selected_aspect = st.selectbox("Select Aspect", aspect_list)

fa = df[df["aspect_norm"] == selected_aspect]

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### ESG Dimension")
    st.bar_chart(fa["esg_norm"].value_counts())

with c2:
    st.markdown("### Sentiment")
    st.bar_chart(fa["sentiment_norm"].value_counts())

with c3:
    st.markdown("### Role / Type")
    st.bar_chart(fa["role_norm"].value_counts())

st.markdown("### 📄 Sentences for This Aspect")
st.dataframe(fa[[sentence_col, esg_col, sentiment_col, role_col]], use_container_width=True)

# =====================================================
# CONFUSION TABLE (ASPECT vs ESG)
# =====================================================

st.subheader("🔀 Aspect vs ESG Dimension Confusion Table")

pivot = pd.pivot_table(
    df,
    index="aspect_norm",
    columns="esg_norm",
    values="sentence_norm",
    aggfunc="count",
    fill_value=0,
)

st.dataframe(pivot, use_container_width=True)

# =====================================================
# DOWNLOAD AGGREGATES
# =====================================================

st.subheader("📥 Download Aggregates")

c1, c2 = st.columns(2)

with c1:
    st.download_button(
        "Download Sentence Consistency CSV",
        consistency.to_csv(index=False).encode("utf-8"),
        "sentence_consistency.csv",
        mime="text/csv",
    )

with c2:
    st.download_button(
        "Download Aspect-ESG Table CSV",
        pivot.to_csv().encode("utf-8"),
        "aspect_esg_confusion.csv",
        mime="text/csv",
    )
