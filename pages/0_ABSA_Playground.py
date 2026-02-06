import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import json
import datetime
import os

from services.openrouter_client import call_openrouter

# =====================================================
# PATH + ENV SETUP
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
if not (BASE_DIR / "outputs").exists():
    BASE_DIR = BASE_DIR.parent

load_dotenv(dotenv_path=BASE_DIR / ".env")

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="ABSA PDF Playground", layout="wide")
st.title("🧪 ABSA Playground — PDF Pages ➜ LLM ➜ Logs")

# =====================================================
# SIDEBAR — SETTINGS
# =====================================================

st.sidebar.header("⚙️ Settings")

prompt_mode = st.sidebar.radio("Prompting Mode", ["Zero-shot", "Few-shot"])
reasoning_mode = st.sidebar.selectbox("Reasoning Mode", ["Direct Answer", "Chain-of-Thought"])

# =====================================================
# OUTPUTS ROOT (FIXED)
# =====================================================

st.sidebar.subheader("📂 Outputs Root")

outputs_root = BASE_DIR / "outputs"
st.sidebar.caption(f"{outputs_root}")

if not outputs_root.exists():
    st.sidebar.error("❌ outputs/ directory not found.")
    pdf_folders = []
else:
    pdf_folders = [p for p in outputs_root.iterdir() if p.is_dir() and p.name.endswith("_pdf")]

# =====================================================
# INPUT SOURCE
# =====================================================

st.sidebar.subheader("📄 Input Source")

input_mode = st.sidebar.radio("User Input From", ["Manual Input", "Select PDF Page (.md)"])

page_text = ""
selected_page = None

if input_mode == "Select PDF Page (.md)":

    if not pdf_folders:
        st.sidebar.error("❌ No *_pdf folders found in outputs/")
    else:
        selected_pdf = st.sidebar.selectbox(
            "PDF Folder",
            pdf_folders,
            format_func=lambda p: p.name
        )

        pages_dir = selected_pdf / "pages"

        if not pages_dir.exists():
            st.sidebar.error("❌ pages/ folder not found.")
        else:
            page_files = sorted(pages_dir.glob("*.md"))

            if not page_files:
                st.sidebar.error("❌ No page_XXX.md files found.")
            else:
                selected_page = st.sidebar.selectbox(
                    "Page File",
                    page_files,
                    format_func=lambda p: p.name
                )

                page_text = selected_page.read_text(encoding="utf-8", errors="ignore")
                st.sidebar.success(f"Loaded: {selected_page.name}")

# =====================================================
# MODEL SELECTION
# =====================================================

st.sidebar.subheader("🤖 Model Selection")

MODEL_OPTIONS = {
    "Fast / Lightweight": {
        "Mistral 7B": "mistralai/mistral-7b-instruct",
        "Gemma 2B": "google/gemma-2b-it",
    },
    "Reasoning / General": {
        "DeepSeek R1": "deepseek/deepseek-r1",
    },
}

category = st.sidebar.selectbox("Category", list(MODEL_OPTIONS.keys()))
model_label = st.sidebar.selectbox("Model", list(MODEL_OPTIONS[category].keys()))
model_name = MODEL_OPTIONS[category][model_label]

st.sidebar.caption(f"Using: {model_name}")

temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.3, 0.1)
max_tokens = st.sidebar.slider("Max Tokens", 256, 4096, 1500, 128)

# =====================================================
# MAIN UI — PROMPTS
# =====================================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 System Prompt")

    system_prompt = st.text_area(
        "Instructions",
        height=260,
        value=(
            "You are an Aspect-Based Sentiment Analysis (ABSA) model.\n\n"
            "Task:\n"
            "1. Identify ESG-related aspects in the text.\n"
            "2. Assign sentiment: Positive, Neutral, or Negative.\n"
            "3. Provide short evidence quote.\n\n"
            "Output JSON list:\n"
            "[{aspect, sentiment, evidence}]"
        )
    )

with col2:
    st.subheader("🙋 User Prompt")

    if input_mode == "Manual Input":
        user_prompt = st.text_area("Input text", height=300)
    else:
        st.markdown("### Page Content (Preview)")
        user_prompt = st.text_area(
            "Loaded page text",
            value=page_text[:8000],
            height=300
        )

# =====================================================
# RUN LLM
# =====================================================

if st.button("🚀 Run LLM", type="primary"):

    if not user_prompt.strip():
        st.warning("Please provide input text.")
        st.stop()

    final_system_prompt = system_prompt

    if reasoning_mode == "Chain-of-Thought":
        final_system_prompt += "\n\nExplain your reasoning step-by-step before final answer."

    messages = [
        {"role": "system", "content": final_system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    with st.spinner("Calling OpenRouter..."):
        try:
            output = call_openrouter(
                messages=messages,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            st.subheader("✅ Model Output")
            st.code(output, language="json")

            # =====================================================
            # SAVE LOG
            # =====================================================

            logs_dir = BASE_DIR / "logs"
            logs_dir.mkdir(exist_ok=True)

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

            log_data = {
                "timestamp": ts,
                "model": model_name,
                "system_prompt": final_system_prompt,
                "user_prompt": user_prompt,
                "output": output,
                "page_file": str(selected_page) if selected_page else None,
            }

            log_path = logs_dir / f"absa_log_{ts}.json"
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2)

            st.success(f"Saved log: {log_path.name}")

            with st.expander("📨 Sent Messages (Debug)"):
                st.json(messages)

        except Exception as e:
            st.error(str(e))

# =====================================================
# FOOTER DEBUG
# =====================================================

st.sidebar.divider()
st.sidebar.caption(f"Project root: {BASE_DIR}")
st.sidebar.caption(f"API key loaded: {bool(os.getenv('OPENROUTER_API_KEY'))}")


# import streamlit as st
# from dotenv import load_dotenv
# from pathlib import Path
# from datetime import datetime
# import json

# load_dotenv()

# from services.openrouter_client import call_openrouter
# from ui.fewshot import render_fewshot_editor
# from models import FREE_MODELS

# # =====================================================
# # Page Setup
# # =====================================================
# st.set_page_config(page_title="ABSA Playground (OpenRouter)", layout="wide")
# st.title("🧪 ABSA Playground — PDF Page → LLM → Logs")

# # =====================================================
# # Sidebar Settings
# # =====================================================
# st.sidebar.header("⚙️ Settings")

# mode = st.sidebar.radio("Prompting Mode", ["Zero-shot", "Few-shot"])

# reasoning_mode = st.sidebar.selectbox(
#     "Reasoning Mode",
#     ["Direct Answer", "Explain Step-by-Step", "Hidden Reasoning"]
# )

# # ---------- Input source
# st.sidebar.subheader("📄 Input Source")

# input_mode = st.sidebar.radio(
#     "User Input From",
#     ["Manual Input", "Load from Page (.md)"]
# )

# page_path = None
# if input_mode == "Load from Page (.md)":
#     page_path = st.sidebar.text_input(
#         "Markdown Page Path",
#         value="outputs/c09205260-2_pdf/pages/page_000.md"
#     )

# # ---------- Model selection
# st.sidebar.subheader("🧠 Model Selection")

# group = st.sidebar.selectbox("Category", list(FREE_MODELS.keys()))
# model_label = st.sidebar.selectbox("Model", list(FREE_MODELS[group].keys()))
# model = FREE_MODELS[group][model_label]

# st.sidebar.caption(f"Using: `{model}`")

# temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.3, 0.1)
# max_tokens = st.sidebar.slider("Max Tokens", 256, 4096, 1500, 128)

# # =====================================================
# # Prompt Inputs
# # =====================================================
# col1, col2 = st.columns(2)

# with col1:
#     st.subheader("🧠 System Prompt")
#     system_prompt = st.text_area(
#         "Instructions",
#         value=(
#             "You are an Aspect-Based Sentiment Analysis (ABSA) model.\n\n"
#             "Task:\n"
#             "1. Identify ESG-related aspects in the text.\n"
#             "2. Assign sentiment: Positive, Neutral, or Negative.\n"
#             "3. Provide short evidence.\n\n"
#             "Output JSON array with fields: aspect, sentiment, evidence."
#         ),
#         height=200,
#     )

#     st.subheader("🙋 User Prompt")

#     if input_mode == "Load from Page (.md)" and page_path:
#         try:
#             with open(page_path, "r", encoding="utf-8") as f:
#                 user_prompt = f.read()
#             st.success(f"Loaded from: {page_path}")
#             st.text_area("Page Content", user_prompt, height=260)
#         except Exception as e:
#             st.error(f"Failed to load file: {e}")
#             user_prompt = ""
#     else:
#         user_prompt = st.text_area("Input text", height=260)

# with col2:
#     if mode == "Few-shot":
#         fewshot_examples = render_fewshot_editor()
#     else:
#         st.info("Zero-shot mode: only system + user prompt will be sent.")
#         fewshot_examples = []

# # =====================================================
# # Run Inference
# # =====================================================
# if st.button("🚀 Run LLM", type="primary"):

#     if not user_prompt.strip():
#         st.warning("No input text.")
#         st.stop()

#     sys_prompt = system_prompt

#     if reasoning_mode == "Explain Step-by-Step":
#         sys_prompt += "\n\nExplain reasoning step by step, then output final JSON."

#     elif reasoning_mode == "Hidden Reasoning":
#         sys_prompt += "\n\nThink step by step internally, but only output JSON."

#     messages = [{"role": "system", "content": sys_prompt}]

#     if mode == "Few-shot":
#         for ex in fewshot_examples:
#             if ex["q"].strip() and ex["a"].strip():
#                 messages.append({"role": "user", "content": ex["q"]})
#                 messages.append({"role": "assistant", "content": ex["a"]})

#     messages.append({"role": "user", "content": user_prompt})

#     with st.spinner("Calling OpenRouter..."):
#         try:
#             output = call_openrouter(
#                 messages=messages,
#                 model=model,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#             )

#             st.subheader("✅ Model Output")
#             st.text_area("Model Output", output, height=350)

#             # ===================== SAVE LOGS =====================
#             ts = datetime.now().strftime("%Y%m%d_%H%M%S")

#             log_dir = Path("outputs/logs")
#             res_dir = Path("outputs/results")
#             log_dir.mkdir(parents=True, exist_ok=True)
#             res_dir.mkdir(parents=True, exist_ok=True)

#             log_data = {
#                 "timestamp": ts,
#                 "model": model,
#                 "temperature": temperature,
#                 "max_tokens": max_tokens,
#                 "reasoning_mode": reasoning_mode,
#                 "prompting_mode": mode,
#                 "system_prompt": sys_prompt,
#                 "messages": messages,
#                 "output": output,
#                 "source_file": page_path if input_mode == "Load from Page (.md)" else None,
#             }

#             log_path = log_dir / f"{ts}.json"
#             with open(log_path, "w", encoding="utf-8") as f:
#                 json.dump(log_data, f, indent=2, ensure_ascii=False)

#             result_path = res_dir / f"{ts}.txt"
#             with open(result_path, "w", encoding="utf-8") as f:
#                 f.write(output)

#             st.success(f"Saved log → {log_path}")
#             st.success(f"Saved result → {result_path}")

#         except Exception as e:
#             st.error(f"❌ Error: {e}")


# import streamlit as st
# from dotenv import load_dotenv
# load_dotenv()

# from services.openrouter_client import call_openrouter
# from ui.fewshot import render_fewshot_editor
# from models import FREE_MODELS

# # =====================================================
# # Page Setup
# # =====================================================
# st.set_page_config(page_title="LLM Playground (OpenRouter)", layout="wide")
# st.title("🧪 LLM Zero-shot / Few-shot + CoT Playground (OpenRouter)")

# # =====================================================
# # Sidebar Settings
# # =====================================================
# st.sidebar.header("⚙️ Settings")

# # --- Prompting mode
# mode = st.sidebar.radio("Prompting Mode", ["Zero-shot", "Few-shot"])

# # --- Reasoning mode
# reasoning_mode = st.sidebar.selectbox(
#     "Reasoning Mode",
#     ["Direct Answer", "Explain Step-by-Step", "Hidden Reasoning"]
# )

# # --- Model selection
# st.sidebar.subheader("🧠 Model Selection")

# group = st.sidebar.selectbox("Category", list(FREE_MODELS.keys()))
# model_label = st.sidebar.selectbox("Model", list(FREE_MODELS[group].keys()))
# model = FREE_MODELS[group][model_label]

# st.sidebar.caption(f"Using: `{model}`")

# # --- Generation params
# temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
# max_tokens = st.sidebar.slider("Max Tokens", 64, 4096, 1024, 64)

# # =====================================================
# # Prompt Inputs
# # =====================================================
# col1, col2 = st.columns(2)

# with col1:
#     st.subheader("🧠 System Prompt")
#     system_prompt = st.text_area(
#         "Instructions for the assistant",
#         value="You are a helpful and precise assistant.",
#         height=140,
#     )

#     st.subheader("🙋 User Prompt")
#     user_prompt = st.text_area(
#         "User input",
#         height=240,
#         placeholder="Ask something..."
#     )

# with col2:
#     if mode == "Few-shot":
#         fewshot_examples = render_fewshot_editor()
#     else:
#         st.info("Zero-shot mode: only system + user prompt will be sent.")
#         fewshot_examples = []

# # =====================================================
# # Run Inference
# # =====================================================
# if st.button("🚀 Run LLM", type="primary"):

#     if not user_prompt.strip():
#         st.warning("Please enter a user prompt.")
#         st.stop()

#     # -----------------------------------------
#     # Inject Reasoning Instructions
#     # -----------------------------------------
#     sys_prompt = system_prompt

#     if reasoning_mode == "Explain Step-by-Step":
#         sys_prompt += "\n\nExplain your reasoning step by step, then provide the final answer clearly."

#     elif reasoning_mode == "Hidden Reasoning":
#         sys_prompt += "\n\nThink step by step internally, but only output the final answer."

#     # Special handling for DeepSeek R1 style models
#     if "r1" in model.lower():
#         sys_prompt += "\n\nEnd your response with: FINAL ANSWER: <answer>"

#     # -----------------------------------------
#     # Build Messages
#     # -----------------------------------------
#     messages = []

#     if sys_prompt.strip():
#         messages.append({"role": "system", "content": sys_prompt})

#     if mode == "Few-shot":
#         for ex in fewshot_examples:
#             if ex["q"].strip() and ex["a"].strip():
#                 messages.append({"role": "user", "content": ex["q"]})
#                 messages.append({"role": "assistant", "content": ex["a"]})

#     messages.append({"role": "user", "content": user_prompt})

#     # -----------------------------------------
#     # Call OpenRouter
#     # -----------------------------------------
#     with st.spinner("Calling OpenRouter..."):
#         try:
#             output = call_openrouter(
#                 messages=messages,
#                 model=model,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#             )

#             st.subheader("✅ Model Output")
#             st.markdown(output)

#             with st.expander("📨 Sent Messages (Debug)"):
#                 st.json(messages)

#         except Exception as e:
#             st.error(f"❌ Error: {e}")


# import streamlit as st
# from dotenv import load_dotenv
# load_dotenv()

# from services.openrouter_client import call_openrouter
# from ui.fewshot import render_fewshot_editor

# # =====================================================
# # Page Setup
# # =====================================================
# st.set_page_config(page_title="LLM Zero-shot / Few-shot Playground", layout="wide")
# st.title("🧪 LLM Zero-shot & Few-shot Playground (OpenRouter)")

# # =====================================================
# # Sidebar Settings
# # =====================================================
# st.sidebar.header("⚙️ Settings")

# mode = st.sidebar.radio("Prompting Mode", ["Zero-shot", "Few-shot"])

# model = st.sidebar.selectbox(
#     "Model",
#     [
#         "mistralai/mistral-7b-instruct",
#         "meta-llama/llama-3.1-8b-instruct",
#         "openai/gpt-4o-mini",
#         "google/gemma-7b-it",
#     ],
# )

# temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
# max_tokens = st.sidebar.slider("Max Tokens", 64, 2048, 512, 64)

# # =====================================================
# # Prompt Inputs
# # =====================================================
# col1, col2 = st.columns(2)

# with col1:
#     st.subheader("🧠 System Prompt")
#     system_prompt = st.text_area(
#         "Instructions for the assistant",
#         value="You are a helpful assistant.",
#         height=120,
#     )

#     st.subheader("🙋 User Prompt")
#     user_prompt = st.text_area(
#         "User input",
#         height=200,
#         placeholder="Ask something..."
#     )

# with col2:
#     if mode == "Few-shot":
#         fewshot_examples = render_fewshot_editor()
#     else:
#         st.info("Zero-shot mode: only system + user prompt will be sent.")
#         fewshot_examples = []

# # =====================================================
# # Run Inference
# # =====================================================
# if st.button("🚀 Run LLM", type="primary"):

#     if not user_prompt.strip():
#         st.warning("Please enter a user prompt.")
#         st.stop()

#     messages = []

#     if system_prompt.strip():
#         messages.append({"role": "system", "content": system_prompt})

#     if mode == "Few-shot":
#         for ex in fewshot_examples:
#             if ex["q"].strip() and ex["a"].strip():
#                 messages.append({"role": "user", "content": ex["q"]})
#                 messages.append({"role": "assistant", "content": ex["a"]})

#     messages.append({"role": "user", "content": user_prompt})

#     with st.spinner("Calling OpenRouter..."):
#         try:
#             output = call_openrouter(
#                 messages=messages,
#                 model=model,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#             )

#             st.subheader("✅ Model Output")
#             st.markdown(output)

#             with st.expander("📨 Sent Messages (Debug)"):
#                 st.json(messages)

#         except Exception as e:
#             st.error(f"Error: {e}")