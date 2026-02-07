logs\pdf_download_log.jsonl

move data from outputs_ocr to outputs and add endswith("_pdf")
pdf_folders = sorted(
    [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]
)
pages/7_bulk_pdf_multiple_methods.py

https://chatgpt.com/c/6962a029-1b30-8327-bf39-3d04345f4207

https://chatgpt.com/c/6963c969-2f58-8328-9878-3deca7c7b313

https://github.com/darisdzakwanhoesien2/summer_traineeship/tree/main/graph_rag_ollama_success/pdf_processing/workflows

logs/pdf_download_log.jsonl

Yes — we can build a **Streamlit OCR app using Mistral OCR**, where users upload images/PDFs, OCR is run via Mistral API, and the **text can be downloaded**. Below is a clean **project structure + complete starter code**.

https://openrouter.ai/models?q=free&fmt=table

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

```

---

# ✅ utils/file_utils.py

```python

```

---

# ✅ app.py (Streamlit App)

```python

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

https://chatgpt.com/c/69616a05-1e00-832e-bb0b-0e7e60f6b5ee

https://chatgpt.com/c/69616a50-413c-8329-8817-1bc93ce5409a

Nice idea 👍 — this is very useful for prompt engineering experiments.

Below is a **complete Streamlit app** that lets you:

* ✅ Choose **Zero-shot / Few-shot**
* ✅ Enter **system + user prompt**
* ✅ Add **few-shot examples (Q/A pairs)**
* ✅ Select **OpenRouter model**
* ✅ Call OpenRouter API and show response

---

# ✅ Project Structure

```
llm_playground/
├── app.py
├── services/
│   └── openrouter_client.py
├── ui/
│   └── fewshot.py
├── .env
├── requirements.txt
```

---

# ✅ requirements.txt

```
streamlit
requests
python-dotenv
```

Install:

```bash
pip install -r requirements.txt
```

---

# ✅ .env

Create `.env` file:

```env
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxx
```

---

# ✅ services/openrouter_client.py

```python

```

---

# ✅ ui/fewshot.py

```python

```

---

# ✅ app.py (Main App)

```python

```

---

# ▶️ Run the App

From project root:

```bash
streamlit run app.py
```

---

# 🚀 Next-Level Upgrades (Good for You 👀)

Given your background in NLP + ML projects, next upgrades could be:

### ✅ Prompt Dataset Mode

Upload CSV/JSON of prompts and run batch inference.

### ✅ Evaluation Mode

Compare:

* zero-shot vs few-shot
* multiple models
* BLEU / ROUGE / embedding similarity

### ✅ Prompt Templates

Save:

* system prompt templates
* few-shot libraries

### ✅ Cost Tracking

Estimate token usage per model (OpenRouter pricing).

---

If you want, next I can give you:

* 📁 Version with **batch CSV testing**
* 📊 Version with **model comparison side-by-side**
* 🧠 Version with **automatic few-shot retrieval (RAG-style)**

Just tell me which direction you want to go.


Great follow-up, Daris — this is exactly where zero/few-shot playgrounds become **real research + product tooling** 👍

I’ll cover:

1. ✅ How to add **Chain-of-Thought (CoT) mode** in your Streamlit + OpenRouter app
2. ✅ Safe way: **Hidden CoT vs Short Reasoning** (best practice)
3. ✅ Prompt strategies: Zero-shot CoT, Few-shot CoT, Self-consistency
4. ✅ Fine-tuning strategy (when + how)
5. ✅ Practical pipeline: from playground → dataset → fine-tuned model

---

# ✅ 1. Adding Chain-of-Thought Mode in Your App

### 🔹 UI: Reasoning Mode Selector

Add in sidebar:

```python
reasoning_mode = st.sidebar.selectbox(
    "Reasoning Mode",
    [
        "Direct Answer",
        "Explain Step-by-Step",
        "Hidden Reasoning (Answer Only)",
    ]
)
```

---

### 🔹 Prompt Injection Strategy

Before building `messages`, modify system prompt:

```python
if reasoning_mode == "Explain Step-by-Step":
    system_prompt += "\nPlease explain your reasoning step by step before giving the final answer."

elif reasoning_mode == "Hidden Reasoning (Answer Only)":
    system_prompt += (
        "\nThink step by step internally, but only output the final answer."
    )
```

👉 This is aligned with current LLM safety practice:

* Model reasons internally
* User only sees concise answer

---

### 🔹 Few-shot with CoT Examples

Few-shot examples should include reasoning:

**User:**

> If I have 3 apples and buy 2 more, how many?

**Assistant:**

> Step 1: Start with 3 apples.
> Step 2: Buy 2 more → total = 5.
> Final answer: 5

Your few-shot editor already supports this — just put reasoning inside `a`.

---

# ✅ 2. Best Practice: Visible vs Hidden CoT

| Mode                 | When to Use                             |
| -------------------- | --------------------------------------- |
| Explain Step-by-Step | Education, debugging, research          |
| Hidden Reasoning     | Production apps, exams, sensitive logic |
| Direct Answer        | Speed + cost saving                     |

👉 Many models now follow:

> “Think silently, answer briefly”

This reduces hallucinated reasoning.

---

# ✅ 3. Advanced Reasoning Prompting Strategies

### ✅ Zero-shot CoT

Add to system:

> Let’s think step by step.

Works surprisingly well for math, logic, planning.

---

### ✅ Few-shot CoT

Provide 2–4 examples with reasoning, then final query.

This is **very powerful** and often beats fine-tuning for small tasks.

---

### ✅ Self-Consistency (Advanced)

Run same prompt multiple times:

* temperature = 0.7
* collect 5 answers
* majority vote / semantic clustering

Good for:

* math
* logical QA
* classification

You can later extend your app to:

```text
Runs = 5 → aggregate answers
```

---

# ✅ 4. When Do You Actually Need Fine-Tuning?

Fine-tuning is useful when:

✅ Task is repetitive & structured
✅ You have >500 good examples
✅ Prompting becomes very long / expensive
✅ Domain language is specific (medical, legal, ESG, parliamentary — your area 👀)

Not good when:

❌ You only want better reasoning
❌ Task changes often
❌ Data is small (<200 samples)

---

# ✅ 5. Fine-Tuning Strategy (Modern LLMOps Way)

## 🧩 Step 1 — Log Playground Interactions

From your app, save:

```json
{
  "system": "...",
  "messages": [...],
  "output": "...",
  "rating": 1-5
}
```

Store as:

* JSONL
* or CSV

This becomes **training data** later.

---

## 🧩 Step 2 — Clean Dataset

Convert to format:

### Instruction Tuning Format

```json
{
  "instruction": "Classify ESG risk",
  "input": "Company dumped waste...",
  "output": "High environmental risk"
}
```

Or Chat format:

```json
{
  "messages": [
    {"role":"system","content":"..."},
    {"role":"user","content":"..."},
    {"role":"assistant","content":"..."}
  ]
}
```

---

## 🧩 Step 3 — Choose Fine-Tuning Method

### 🔹 Option A: LoRA / QLoRA (Recommended)

Train adapters only.

Tools:

* HuggingFace PEFT
* Axolotl
* Unsloth (fastest)

Works on:

* LLaMA
* Mistral
* Gemma

GPU: even RTX 3060 can work.

---

### 🔹 Option B: OpenAI / OpenRouter Hosted FT

Easier but:

* expensive
* less control
* model-limited

Good for production pipelines.

---

## 🧩 Step 4 — Evaluate vs Prompting

Always compare:

| Method     | Accuracy | Cost | Latency |
| ---------- | -------- | ---- | ------- |
| Zero-shot  | low      | low  | low     |
| Few-shot   | high     | high | medium  |
| Fine-tuned | high     | low  | low     |

Often best solution:

> Fine-tuned + short prompt

---

# ✅ 6. Suggested Pipeline for You (Given Your Projects)

Since you work on:

* ESG
* policy debates
* multimodal sentiment
* KG-RAG

🔥 Best strategy:

### Phase 1 — Prompt Playground (current app)

* test tasks
* collect logs
* find failure cases

### Phase 2 — Auto Dataset Builder

Streamlit:

* approve good answers
* label errors
* export JSONL

### Phase 3 — Fine-tune Domain Model

* Mistral 7B LoRA
* ESG classifier
* Policy stance detector

### Phase 4 — RAG + Fine-tuned Hybrid

* RAG for facts
* Fine-tune for reasoning style & labeling

This is **exactly what industry ESG intelligence systems use**.

---

# 🚀 If You Want, Next I Can Give You

I can continue with **code-level upgrades**:

### 🔥 Option 1 — Add Chain-of-Thought Toggle + Self-Consistency

→ full Streamlit code

### 🔥 Option 2 — Add Logging + Dataset Export

→ build fine-tuning dataset automatically

### 🔥 Option 3 — Fine-tuning Script (QLoRA with Mistral)

→ training + inference code

### 🔥 Option 4 — RAG + Few-shot Hybrid Architecture

Tell me which one you want first and I’ll go deep into implementation.


https://chatgpt.com/c/69616a50-413c-8329-8817-1bc93ce5409a

https://chatgpt.com/c/6966bc72-1724-8332-b146-92ee17716dad

Got it 👍 — instead of **uploading PDFs**, we’ll:

✅ Read PDFs directly from
`data/sustainability_pdfs/<company>/<pdf files>`
✅ Allow selecting **multiple companies and PDFs**
✅ Run OCR on those files
✅ Store only **OCR outputs** (no re-saving PDFs)
✅ Remain **resume-safe via log**
✅ ZIP only OCR outputs

Below is a **complete Streamlit page** replacing the upload logic with folder-based selection.

---

# ✅ Folder-Based Bulk OCR (Multi-Company, Resume Safe)

### 📁 Expected structure

```
data/
└── sustainability_pdfs/
    ├── charoen/
    │   ├── report_1.pdf
    │   └── report_2.pdf
    ├── unilever/
    │   └── sustainability_2023.pdf
```

---

## ✅ Full Streamlit Page Code

```python
import streamlit as st
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import zipfile
import base64
import time
import json

# =====================================================
# PATH & ENV
# =====================================================

BASE_DIR = Path(__file__).parents[1]
load_dotenv(BASE_DIR / ".env")

API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    st.error("❌ MISTRAL_API_KEY not found in .env")
    st.stop()

BASE = "https://api.mistral.ai/v1"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

PDF_ROOT = BASE_DIR / "data" / "sustainability_pdfs"
OUT_DIR = BASE_DIR / "outputs_ocr"
LOG_DIR = BASE_DIR / "logs"

OUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "bulk_ocr_log.json"

# =====================================================
# STREAMLIT CONFIG
# =====================================================

st.set_page_config(page_title="📚 Bulk OCR — Sustainability PDFs", layout="wide")
st.title("📚 Bulk OCR from Sustainability PDF Folders (Mistral OCR)")

st.markdown("""
### Pipeline
1. Select company folders  
2. Select PDFs  
3. Upload to Mistral via signed URL  
4. Run OCR  
5. Save pages + images per document  
6. Resume-safe (skip processed)  
7. Download all OCR outputs as ZIP  
""")

# =====================================================
# UTIL
# =====================================================

def safe_name(name: str):
    return name.replace("/", "_").replace("\\", "_")

def load_log():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {}

def save_log(log):
    LOG_FILE.write_text(json.dumps(log, indent=2))


# =====================================================
# COMPANY & PDF SELECTION
# =====================================================

if not PDF_ROOT.exists():
    st.error(f"❌ Folder not found: {PDF_ROOT}")
    st.stop()

companies = sorted([p for p in PDF_ROOT.iterdir() if p.is_dir()])

selected_companies = st.multiselect(
    "🏢 Select companies",
    companies,
    format_func=lambda p: p.name,
)

selected_pdfs = []

for comp in selected_companies:
    pdfs = sorted(comp.glob("*.pdf"))
    if pdfs:
        chosen = st.multiselect(
            f"📄 Select PDFs for {comp.name}",
            pdfs,
            default=pdfs,
            format_func=lambda p: p.name,
        )
        selected_pdfs.extend(chosen)

st.info(f"Total selected PDFs: {len(selected_pdfs)}")

# =====================================================
# RUN OCR
# =====================================================

if "ocr_done" not in st.session_state:
    st.session_state["ocr_done"] = False

if selected_pdfs and st.button("🚀 Run BULK OCR Pipeline"):

    st.session_state["ocr_done"] = False

    log = load_log()

    progress = st.progress(0)
    status = st.empty()

    total = len(selected_pdfs)

    for i, pdf_path in enumerate(selected_pdfs, start=1):

        company = pdf_path.parent.name
        doc_key = f"{company}/{pdf_path.name}"

        status.info(f"Processing {i}/{total}: {doc_key}")

        if doc_key in log and log[doc_key]["status"] == "done":
            status.warning(f"⏭ Skipped (already processed): {doc_key}")
            progress.progress(i / total)
            continue

        doc_name = pdf_path.stem
        out_root = OUT_DIR / company / doc_name
        pages_dir = out_root / "pages"
        images_dir = out_root / "images"
        pages_dir.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            # ---------------- Upload ----------------
            with open(pdf_path, "rb") as f:
                r = requests.post(
                    f"{BASE}/files",
                    headers=HEADERS,
                    files={"file": (pdf_path.name, f)},
                    data={"purpose": "ocr"},
                    timeout=120,
                )
            if r.status_code != 200:
                raise RuntimeError(f"Upload failed: {r.text}")
            file_id = r.json()["id"]

            # ---------------- Signed URL ----------------
            r = requests.get(
                f"{BASE}/files/{file_id}/url",
                headers=HEADERS,
                timeout=60,
            )
            if r.status_code != 200:
                raise RuntimeError(f"Signed URL failed: {r.text}")
            signed_url = r.json()["url"]

            # ---------------- OCR ----------------
            payload = {
                "model": "mistral-ocr-latest",
                "document": {
                    "type": "document_url",
                    "document_url": signed_url,
                },
                "include_image_base64": True,
            }

            r = requests.post(
                f"{BASE}/ocr",
                headers={**HEADERS, "Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            if r.status_code != 200:
                raise RuntimeError(f"OCR failed: {r.text}")

            result = r.json()

            # ---------------- Save Pages ----------------
            pages = result.get("pages", [])
            for p in pages:
                idx = p.get("index", 0)
                md = p.get("markdown", "")

                (pages_dir / f"page_{idx:04d}.md").write_text(md, encoding="utf-8")

                for img in p.get("images", []):
                    if img.get("image_base64"):
                        img_bytes = base64.b64decode(img["image_base64"])
                        raw_name = img.get("id", f"img_{idx}.jpg")
                        img_name = Path(raw_name).name
                        (images_dir / img_name).write_bytes(img_bytes)

            log[doc_key] = {
                "status": "done",
                "company": company,
                "pages": len(pages),
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_log(log)

        except Exception as e:
            log[doc_key] = {"status": "failed", "error": str(e)}
            save_log(log)
            st.error(f"❌ Failed: {doc_key}")
            st.exception(e)

        progress.progress(i / total)
        time.sleep(0.2)

    status.success("✅ Bulk OCR completed!")
    st.session_state["ocr_done"] = True


# =================================================
# OUTPUT DOWNLOAD
# =================================================

if OUT_DIR.exists() and any(OUT_DIR.rglob("pages")):

    zip_path = BASE_DIR / "bulk_ocr_outputs.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in OUT_DIR.rglob("*"):
            if p.is_file():
                z.write(p, arcname=p.relative_to(OUT_DIR))

    with open(zip_path, "rb") as f:
        st.download_button(
            "⬇ Download ALL OCR Results (ZIP)",
            data=f,
            file_name="bulk_ocr_outputs.zip",
            mime="application/zip",
        )

    st.divider()

    # =================================================
    # PREVIEW
    # =================================================

    st.subheader("🔍 Preview OCR Output")

    companies_out = sorted([p for p in OUT_DIR.iterdir() if p.is_dir()])

    company_sel = st.selectbox("Company", companies_out, format_func=lambda p: p.name)

    docs = sorted([p for p in company_sel.iterdir() if p.is_dir()])

    doc = st.selectbox("Document", docs, format_func=lambda p: p.name)

    pages = sorted((doc / "pages").glob("*.md"))
    images = sorted((doc / "images").glob("*"))

    if pages:
        page = st.selectbox("Page", pages, format_func=lambda p: p.name)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### OCR Text")
            st.text_area(
                "",
                value=page.read_text(encoding="utf-8", errors="ignore"),
                height=500,
            )

        with col2:
            st.markdown("### Images")
            for img in images:
                st.image(str(img), use_container_width=True)
```

---

## 🔥 What This Version Solves for You

Perfect for your **ESG thesis preprocessing pipeline**:

* ✔ No upload needed (direct dataset processing)
* ✔ Multi-company batching
* ✔ Resume-safe for long OCR runs
* ✔ Clean output structure:

  ```
  outputs_ocr/
    └── company/
        └── report_name/
            ├── pages/
            └── images/
  ```
* ✔ Easy downstream:

  * LLM parsing
  * Question extraction
  * ABSA / ESG tagging

---

## If you want, next step I can help you with

Given your earlier goals (OCR → LLM → question parsing / ESG extraction), I can next add:

* 🔹 Auto sentence chunking
* 🔹 LLM parsing into structured JSON
* 🔹 Question / table / KPI detection
* 🔹 Auto registry per PDF

Just tell me which pipeline you want to attach after OCR:
**(A) Question bank parsing**, **(B) ESG KPI extraction**, or **(C) Both**.
