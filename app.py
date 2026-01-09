import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import shutil

load_dotenv()

from mistral_api import upload_file_for_ocr, get_signed_url, run_ocr_from_url
from ocr_utils import extract_pages, save_pages_and_images


st.set_page_config(page_title="Thesis OCR Pipeline", layout="wide")
st.title("📘 Thesis OCR Preprocessing (Mistral)")

uploaded = st.file_uploader(
    "Upload thesis PDF or scanned images",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded:

    tmp = Path("tmp_upload")
    tmp.write_bytes(uploaded.getbuffer())

    doc_name = uploaded.name.replace(".", "_")
    out_root = Path("outputs") / doc_name

    if st.button("Run Full OCR Pipeline"):

        if out_root.exists():
            shutil.rmtree(out_root)

        with st.spinner("Uploading to Mistral..."):
            file_id = upload_file_for_ocr(tmp)

        with st.spinner("Getting signed URL..."):
            url = get_signed_url(file_id)

        with st.spinner("Running OCR (this may take time)..."):
            result = run_ocr_from_url(url)

        with st.spinner("Saving pages and images..."):
            pages = extract_pages(result)
            save_pages_and_images(pages, out_root)

        st.success(f"OCR completed: {len(pages)} pages extracted")

        # -------- ZIP EXPORT --------
        zip_path = out_root.with_suffix(".zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in out_root.rglob("*"):
                z.write(p, arcname=p.relative_to(out_root))

        with open(zip_path, "rb") as f:
            st.download_button(
                "⬇ Download Structured OCR Output (ZIP)",
                data=f,
                file_name=f"{doc_name}_ocr.zip",
                mime="application/zip"
            )

        st.subheader("📁 Output Preview")
        st.write("Pages:", len(list((out_root / "pages").glob("*.md"))))
        st.write("Images:", len(list((out_root / "images").glob("*.jpg"))))

# import streamlit as st
# from dotenv import load_dotenv

# from services.mistral_api import test_auth, run_ocr
# from utils.file_utils import save_upload, save_text

# load_dotenv()

# st.set_page_config(page_title="Mistral OCR Debugger", layout="wide")
# st.title("🔎 Mistral OCR + Auth Debug Tool")

# st.markdown("This app verifies your API key and runs OCR.")

# # -----------------------
# # AUTH TEST
# # -----------------------
# st.subheader("1️⃣ Test API Key")

# if st.button("Test Authentication"):
#     with st.spinner("Checking /v1/models ..."):
#         code, text = test_auth()

#     if code == 200:
#         st.success("API key is VALID ✅")
#     else:
#         st.error(f"Auth failed ❌ ({code})")
#         st.code(text)

# # -----------------------
# # OCR
# # -----------------------
# st.subheader("2️⃣ Run OCR")

# file = st.file_uploader(
#     "Upload Image or PDF",
#     type=["png", "jpg", "jpeg", "pdf"]
# )

# if file:

#     if st.button("Run OCR"):
#         with st.spinner("Calling Mistral OCR..."):
#             try:
#                 path = save_upload(file)

#                 text, raw = run_ocr(str(path))

#                 st.success("OCR completed")

#                 st.text_area("Extracted Text", text, height=350)

#                 txt_path = save_text(text)

#                 with open(txt_path, "rb") as f:
#                     st.download_button(
#                         "⬇ Download TXT",
#                         data=f,
#                         file_name=txt_path.name
#                     )

#                 with st.expander("Raw API Response"):
#                     st.json(raw)

#             except Exception as e:
#                 st.error("OCR Failed")
#                 st.code(str(e))


# import streamlit as st
# from dotenv import load_dotenv

# from services.mistral_ocr import run_ocr
# from utils.file_utils import save_uploaded_file, save_text

# load_dotenv()

# st.set_page_config(page_title="Mistral OCR App", layout="wide")
# st.title("📄 Mistral OCR — Image & PDF to Text")

# st.markdown("""
# Upload an **image or PDF**, run OCR using **Mistral**,  
# preview extracted text, and download the result.
# """)

# uploaded = st.file_uploader(
#     "Upload Image or PDF",
#     type=["png", "jpg", "jpeg", "pdf"]
# )

# if uploaded:
#     st.info("File uploaded successfully.")

#     if st.button("🔍 Run OCR"):
#         with st.spinner("Running OCR via Mistral..."):
#             try:
#                 file_path = save_uploaded_file(uploaded)

#                 text, raw = run_ocr(str(file_path))

#                 st.success("OCR completed!")

#                 st.subheader("📜 Extracted Text")
#                 st.text_area(
#                     "OCR Output",
#                     value=text,
#                     height=350
#                 )

#                 txt_path = save_text(text)

#                 with open(txt_path, "rb") as f:
#                     st.download_button(
#                         "⬇️ Download Text (.txt)",
#                         data=f,
#                         file_name=txt_path.name,
#                         mime="text/plain"
#                     )

#                 with st.expander("🔧 Raw API Response"):
#                     st.json(raw)

#             except Exception as e:
#                 st.error("OCR failed")
#                 st.code(str(e))