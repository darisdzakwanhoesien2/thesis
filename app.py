import streamlit as st
from dotenv import load_dotenv

from services.mistral_ocr import run_ocr
from utils.file_utils import save_uploaded_file, save_text

load_dotenv()

st.set_page_config(page_title="Mistral OCR App", layout="wide")
st.title("📄 Mistral OCR — Image & PDF to Text")

st.markdown("""
Upload an **image or PDF**, run OCR using **Mistral**,  
preview extracted text, and download the result.
""")

uploaded = st.file_uploader(
    "Upload Image or PDF",
    type=["png", "jpg", "jpeg", "pdf"]
)

if uploaded:
    st.info("File uploaded successfully.")

    if st.button("🔍 Run OCR"):
        with st.spinner("Running OCR via Mistral..."):
            try:
                file_path = save_uploaded_file(uploaded)

                text, raw = run_ocr(str(file_path))

                st.success("OCR completed!")

                st.subheader("📜 Extracted Text")
                st.text_area(
                    "OCR Output",
                    value=text,
                    height=350
                )

                txt_path = save_text(text)

                with open(txt_path, "rb") as f:
                    st.download_button(
                        "⬇️ Download Text (.txt)",
                        data=f,
                        file_name=txt_path.name,
                        mime="text/plain"
                    )

                with st.expander("🔧 Raw API Response"):
                    st.json(raw)

            except Exception as e:
                st.error("OCR failed")
                st.code(str(e))