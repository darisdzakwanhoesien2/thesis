# https://chatgpt.com/c/6964de59-a970-8326-98bb-6d35a45c2561

import streamlit as st
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🔗 ESG-ABSA Research Traceability — Sankey Overview")

st.markdown("""
This Sankey diagram visualizes **end-to-end traceability** from:

**Research Questions → Methodology → Models → Metrics → Code → Evidence**

across the full ESG-ABSA system.
""")

# ==========================================================
# DATA — HIGH-LEVEL FLOWS DERIVED FROM YOUR TABLE
# ==========================================================

flows = [

    # ---------- RQ1 Core Design ----------
    ("RQ1", "Core ESG-ABSA Design", "System-level Pipeline", "Composite ESG-ABSA Pipeline", "Multi-aspect F1", "run_pipeline()", "final_outputs.csv"),

    ("RQ1a", "Structural Awareness", "Hierarchical Encoding", "Hierarchical BERT / BiLSTM", "Context F1", "rq1_hierarchical()", "hierarchy_heatmap.png"),

    ("RQ1b", "Tonal Awareness", "Multi-tone Classification", "Multi-task Tone Head", "Tone F1", "rq2_tone_and_sentiment()", "tone_confusion_matrix.png"),

    ("RQ1c", "Ontology Awareness", "Ontology Injection", "GAT + BERT Fusion", "OCG / Recall@Rare", "rq3_ontology()", "ontology_path_alignment.png"),

    # ---------- RQ2 Integration ----------
    ("RQ2", "Model Integration", "Multi-channel Fine-tuning", "FineTunedESGTrainer", "Macro-F1", "train_finetuned_model()", "training_log.json"),

    # ---------- RQ3 Explainability ----------
    ("RQ3", "Explainability", "Post-hoc XAI", "Captum + Attention", "AFS", "explain_prediction()", "attention_map.html"),

    # ---------- RQ4 Benchmarking ----------
    ("RQ4", "Benchmarking", "Multi-model Comparison", "Benchmark Pipelines", "Runtime / F1", "benchmark_models()", "benchmark_results.csv"),

    # ---------- RQ5 Bias ----------
    ("RQ5", "Bias & Reliability", "Bias Calibration", "Tone Reweighted Loss", "Calibration Error", "analyze_commitment_bias()", "bias_vs_tone_plot.png"),

    # ---------- RQ6 Ontology Alignment ----------
    ("RQ6", "Ontology–Sentiment Alignment", "Graph Embedding Alignment", "Ontology Attention Module", "Alignment Score", "ontology_attention()", "ontology_attention_heatmap.png"),

    # ---------- RQ7 Generalization ----------
    ("RQ7", "Cross-domain Benchmarking", "Domain Transfer Eval", "Multi-domain Pipeline", "Domain F1", "compare_models()", "f1_vs_efficiency_plot.png"),

    # ---------- RQ8 Fairness Optimization ----------
    ("RQ8", "Bias Optimization", "Loss Reweighting", "Fairness-aware BERT", "Bias Reduction %", "reweight_tone_loss()", "fairness_comparison_chart.png"),

    # ---------- RQ9 Efficiency ----------
    ("RQ9", "Efficiency Tradeoff", "Model Profiling", "Inference Profiler", "Latency / Memory", "profile_inference_time()", "model_efficiency.csv"),

    # ---------- RQ10 Reasoning Graph ----------
    ("RQ10", "Explainable Reasoning Graph", "RDF Synthesis", "Reasoning Graph Generator", "Explainability Coverage", "build_esg_graph_rdf()", "esg_reasoning_rdf.ttl"),
]

layers = ["RQ", "Focus", "Method", "Model", "Metric", "Code", "Evidence"]

# ==========================================================
# BUILD NODE LIST
# ==========================================================

all_nodes = []
for row in flows:
    for item in row:
        if item not in all_nodes:
            all_nodes.append(item)

node_index = {n: i for i, n in enumerate(all_nodes)}

# ==========================================================
# BUILD LINKS
# ==========================================================

sources = []
targets = []
values = []

for row in flows:
    for i in range(len(row) - 1):
        sources.append(node_index[row[i]])
        targets.append(node_index[row[i + 1]])
        values.append(1)

# ==========================================================
# SANKEY FIGURE
# ==========================================================

fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=18,
        thickness=18,
        line=dict(color="black", width=0.5),
        label=all_nodes,
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
    )
)])

fig.update_layout(
    title_text="ESG-ABSA Research Question → System Implementation Traceability",
    font_size=11,
    height=900
)

st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# OPTIONAL: FILTER BY RQ
# ==========================================================

st.markdown("---")
st.subheader("🔍 Filter by Research Question")

rq_selected = st.selectbox(
    "Select RQ",
    sorted({f[0] for f in flows})
)

filtered = [f for f in flows if f[0] == rq_selected]

st.write("### Trace Path")
for f in filtered:
    st.markdown(" → ".join(f))
