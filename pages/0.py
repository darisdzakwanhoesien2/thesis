import streamlit as st
from dotenv import load_dotenv
load_dotenv()

from services.openrouter_client import call_openrouter
from ui.fewshot import render_fewshot_editor
from models import FREE_MODELS

# =====================================================
# Page Setup
# =====================================================
st.set_page_config(page_title="LLM Playground (OpenRouter)", layout="wide")
st.title("🧪 LLM Zero-shot / Few-shot + CoT Playground (OpenRouter)")

# =====================================================
# Sidebar Settings
# =====================================================
st.sidebar.header("⚙️ Settings")

# --- Prompting mode
mode = st.sidebar.radio("Prompting Mode", ["Zero-shot", "Few-shot"])

# --- Reasoning mode
reasoning_mode = st.sidebar.selectbox(
    "Reasoning Mode",
    ["Direct Answer", "Explain Step-by-Step", "Hidden Reasoning"]
)

# --- Model selection
st.sidebar.subheader("🧠 Model Selection")

group = st.sidebar.selectbox("Category", list(FREE_MODELS.keys()))
model_label = st.sidebar.selectbox("Model", list(FREE_MODELS[group].keys()))
model = FREE_MODELS[group][model_label]

st.sidebar.caption(f"Using: `{model}`")

# --- Generation params
temperature = st.sidebar.slider("Temperature", 0.0, 1.5, 0.7, 0.1)
max_tokens = st.sidebar.slider("Max Tokens", 64, 4096, 1024, 64)

# =====================================================
# Prompt Inputs
# =====================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("🧠 System Prompt")
    system_prompt = st.text_area(
        "Instructions for the assistant",
        value="You are a helpful and precise assistant.",
        height=140,
    )

    st.subheader("🙋 User Prompt")
    user_prompt = st.text_area(
        "User input",
        height=240,
        placeholder="Ask something..."
    )

with col2:
    if mode == "Few-shot":
        fewshot_examples = render_fewshot_editor()
    else:
        st.info("Zero-shot mode: only system + user prompt will be sent.")
        fewshot_examples = []

# =====================================================
# Run Inference
# =====================================================
if st.button("🚀 Run LLM", type="primary"):

    if not user_prompt.strip():
        st.warning("Please enter a user prompt.")
        st.stop()

    # -----------------------------------------
    # Inject Reasoning Instructions
    # -----------------------------------------
    sys_prompt = system_prompt

    if reasoning_mode == "Explain Step-by-Step":
        sys_prompt += "\n\nExplain your reasoning step by step, then provide the final answer clearly."

    elif reasoning_mode == "Hidden Reasoning":
        sys_prompt += "\n\nThink step by step internally, but only output the final answer."

    # Special handling for DeepSeek R1 style models
    if "r1" in model.lower():
        sys_prompt += "\n\nEnd your response with: FINAL ANSWER: <answer>"

    # -----------------------------------------
    # Build Messages
    # -----------------------------------------
    messages = []

    if sys_prompt.strip():
        messages.append({"role": "system", "content": sys_prompt})

    if mode == "Few-shot":
        for ex in fewshot_examples:
            if ex["q"].strip() and ex["a"].strip():
                messages.append({"role": "user", "content": ex["q"]})
                messages.append({"role": "assistant", "content": ex["a"]})

    messages.append({"role": "user", "content": user_prompt})

    # -----------------------------------------
    # Call OpenRouter
    # -----------------------------------------
    with st.spinner("Calling OpenRouter..."):
        try:
            output = call_openrouter(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            st.subheader("✅ Model Output")
            st.markdown(output)

            with st.expander("📨 Sent Messages (Debug)"):
                st.json(messages)

        except Exception as e:
            st.error(f"❌ Error: {e}")


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