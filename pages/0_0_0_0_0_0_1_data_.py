import streamlit as st
import pandas as pd
from gradio_client import Client
import tempfile
import json

# ============================================================
# CONFIG
# ============================================================

HF_SPACE = "darisdzakwanhoesien/absa-ontology"
client = Client(HF_SPACE)

st.set_page_config(page_title="🧠 ABSA Ontology Explorer", layout="wide")
st.title("🧠 ABSA Ontology API Explorer")
st.caption("Streamlit client for Rule · Classical · Deep · Hybrid · Comparison APIs")

# ============================================================
# INPUT
# ============================================================

default_text = """## TANTANGAN DAN RESPONS TERHADAP ISU KEBERLANJUTAN
The ban on corn imports pushed us to become more self-sufficient by using locally sourced raw materials.
Partnerships with local farmers became vital to secure supply and reduce reliance on international markets.
"""

text = st.text_area("✍️ Input Text", value=default_text, height=200)

mode = st.selectbox(
    "⚙️ Select API Mode",
    [
        "Rule-based",
        "Classical",
        "Deep Learning",
        "Hybrid",
        "Cross-model Sentence Compare"
    ]
)

# ============================================================
# PARAMETER CONTROLS
# ============================================================

epochs = None
tw = None
aw = None
sentence_text = None

if mode in ["Deep Learning", "Hybrid"]:
    epochs = st.slider("Epochs", 1, 10, 3)

if mode == "Hybrid":
    tw = st.slider("Tone Weight (tw)", 0.1, 3.0, 1.5)
    aw = st.slider("Alignment Weight (aw)", 0.0, 1.0, 0.2)

if mode == "Cross-model Sentence Compare":
    sentence_text = st.text_input("Enter a sentence", value="Hello!!")

run = st.button("🚀 Run Inference")

# ============================================================
# UTILITIES
# ============================================================

def dict_to_df(obj):
    """Convert Gradio dataframe dict → Pandas DataFrame"""
    if not isinstance(obj, dict):
        return None
    headers = obj.get("headers", [])
    data = obj.get("data", [])
    if headers and data:
        return pd.DataFrame(data, columns=headers)
    return None


def render_plot(plot_obj):
    """Render serialized plot object safely"""
    if not isinstance(plot_obj, dict):
        return

    plot_type = plot_obj.get("type")
    plot_json = plot_obj.get("plot")

    if plot_type == "plotly":
        import plotly.io as pio
        fig = pio.from_json(plot_json)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Plot type `{plot_type}` not directly supported in Streamlit.")


# ============================================================
# API EXECUTION
# ============================================================

if run:
    with st.spinner("Calling API..."):
        try:
            # -------------------------
            # API Routing
            # -------------------------

            if mode == "Rule-based":
                result = client.predict(text=text, api_name="/_run_rule")

            elif mode == "Classical":
                result = client.predict(text=text, api_name="/_run_classical")

            elif mode == "Deep Learning":
                result = client.predict(
                    text=text,
                    epochs=epochs,
                    api_name="/_run_deep"
                )

            elif mode == "Hybrid":
                result = client.predict(
                    text=text,
                    epochs=epochs,
                    tw=tw,
                    aw=aw,
                    api_name="/_run_hybrid"
                )

            elif mode == "Cross-model Sentence Compare":
                result = client.predict(
                    sentence_text=sentence_text,
                    api_name="/_compare_sentence"
                )

            else:
                st.error("Unknown mode selected.")
                st.stop()

            st.success("✅ Inference completed")

        except Exception as e:
            st.error(f"❌ API call failed: {e}")
            st.stop()

    # ========================================================
    # OUTPUT RENDERING
    # ========================================================

    st.divider()
    st.subheader("📦 Raw API Output")
    st.json(result, expanded=False)

    st.divider()
    st.subheader("📊 Parsed Outputs")

    # Each API returns tuple with mixed types
    for idx, item in enumerate(result):
        st.markdown(f"### Output [{idx}]")

        # -------------------------
        # File path
        # -------------------------
        if isinstance(item, str):
            st.write("📁 File:", item)
            st.info("File download is handled by HuggingFace space.")

        # -------------------------
        # Dataframe dict
        # -------------------------
        elif isinstance(item, dict) and "headers" in item:
            df = dict_to_df(item)
            if df is not None:
                st.dataframe(df, use_container_width=True)

                # CSV download
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"⬇️ Download CSV [{idx}]",
                    csv,
                    file_name=f"output_{idx}.csv",
                    mime="text/csv",
                )

        # -------------------------
        # Plot dict
        # -------------------------
        elif isinstance(item, dict) and "plot" in item:
            render_plot(item)

        # -------------------------
        # Fallback
        # -------------------------
        else:
            st.write(item)
