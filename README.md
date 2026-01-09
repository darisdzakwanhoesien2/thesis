Yes — we can build a **Streamlit OCR app using Mistral OCR**, where users upload images/PDFs, OCR is run via Mistral API, and the **text can be downloaded**. Below is a clean **project structure + complete starter code**.

I’ll keep the API call modular so you can easily swap models/endpoints if Mistral updates them.

---

# ✅ Project Directory Structure

```
mistral_ocr_app/
│
├── app.py                     # Streamlit UI
├── services/
│   └── mistral_ocr.py          # Mistral OCR API wrapper
│
├── utils/
│   └── file_utils.py           # temp file helpers
│
├── outputs/                    # saved OCR results (txt)
│
├── .env                        # API key
├── requirements.txt
└── README.md
```

---

# ✅ requirements.txt

```
streamlit
requests
python-dotenv
Pillow
```

If you want PDF preview later, we can add `pymupdf`.

---

# ✅ .env

```
MISTRAL_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

# ✅ services/mistral_ocr.py

> ⚠️ Endpoint may evolve. This is written in a **configurable way** so you only change URL + payload if needed.

```python
import os
import requests

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Example endpoint — adjust if Mistral updates OCR API
MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}"
}


def run_ocr(file_path: str):
    with open(file_path, "rb") as f:
        files = {
            "file": f
        }

        data = {
            "model": "mistral-ocr-latest"  # or vision-capable model
        }

        response = requests.post(
            MISTRAL_OCR_URL,
            headers=HEADERS,
            files=files,
            data=data,
            timeout=120
        )

    if response.status_code != 200:
        raise RuntimeError(response.text)

    result = response.json()

    # Expected field may differ — adjust if needed
    text = result.get("text", "")

    return text, result
```

---

# ✅ utils/file_utils.py

```python
import uuid
from pathlib import Path


TMP_DIR = Path("outputs")
TMP_DIR.mkdir(exist_ok=True)


def save_uploaded_file(uploaded_file):
    suffix = Path(uploaded_file.name).suffix
    path = TMP_DIR / f"{uuid.uuid4()}{suffix}"

    with open(path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return path


def save_text(text: str):
    path = TMP_DIR / f"ocr_{uuid.uuid4()}.txt"
    path.write_text(text, encoding="utf-8")
    return path
```

---

# ✅ app.py (Streamlit App)

```python
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
```

---

# ✅ Run the App

```bash
cd mistral_ocr_app
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

---

# 🔥 Optional Upgrades (I can give code if you want)

Since you’re doing a lot of Streamlit tooling already, nice additions would be:

### ✅ Batch OCR (multiple files)

Upload many → ZIP download of all results

### ✅ Structured OCR Output

Export as:

* `.txt`
* `.json`
* `.csv` (page-wise)

### ✅ Layout-aware OCR

If Mistral returns bounding boxes:

* Render text blocks
* Table reconstruction

### ✅ OCR → LLM cleanup

Post-process text with:

* paragraph formatting
* heading detection
* table extraction

---

## If you want, next step I can give you:

* ✅ Version using **Mistral Vision Chat API instead of OCR endpoint**
* ✅ Batch OCR with progress bar
* ✅ PDF page-by-page OCR
* ✅ Dockerized version for deployment

Just tell me which direction you want to extend this, and I’ll tailor it to your workflow (same style as your other Streamlit tools).
# thesis
