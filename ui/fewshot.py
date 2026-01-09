import streamlit as st


def render_fewshot_editor():
    st.subheader("📌 Few-shot Examples")

    if "fewshot" not in st.session_state:
        st.session_state.fewshot = [{"q": "", "a": ""}]

    for i, ex in enumerate(st.session_state.fewshot):
        with st.expander(f"Example {i+1}", expanded=True):
            ex["q"] = st.text_area("User Input", ex["q"], key=f"q_{i}")
            ex["a"] = st.text_area("Assistant Output", ex["a"], key=f"a_{i}")

    col1, col2 = st.columns(2)

    if col1.button("➕ Add Example"):
        st.session_state.fewshot.append({"q": "", "a": ""})

    if col2.button("➖ Remove Last") and len(st.session_state.fewshot) > 1:
        st.session_state.fewshot.pop()

    return st.session_state.fewshot


# import streamlit as st


# def render_fewshot_editor():
#     st.subheader("📌 Few-shot Examples")

#     if "fewshot" not in st.session_state:
#         st.session_state.fewshot = [{"q": "", "a": ""}]

#     for i, ex in enumerate(st.session_state.fewshot):
#         with st.expander(f"Example {i+1}", expanded=True):
#             ex["q"] = st.text_area("User Input", ex["q"], key=f"q_{i}")
#             ex["a"] = st.text_area("Assistant Output", ex["a"], key=f"a_{i}")

#     col1, col2 = st.columns(2)

#     if col1.button("➕ Add Example"):
#         st.session_state.fewshot.append({"q": "", "a": ""})

#     if col2.button("➖ Remove Last") and len(st.session_state.fewshot) > 1:
#         st.session_state.fewshot.pop()

#     return st.session_state.fewshot


# import streamlit as st


# def render_fewshot_editor():
#     st.subheader("📌 Few-shot Examples")

#     if "fewshot" not in st.session_state:
#         st.session_state.fewshot = [{"q": "", "a": ""}]

#     for i, ex in enumerate(st.session_state.fewshot):
#         with st.expander(f"Example {i+1}", expanded=True):
#             ex["q"] = st.text_area("User Input", ex["q"], key=f"q_{i}")
#             ex["a"] = st.text_area("Assistant Output", ex["a"], key=f"a_{i}")

#     col1, col2 = st.columns(2)

#     if col1.button("➕ Add Example"):
#         st.session_state.fewshot.append({"q": "", "a": ""})

#     if col2.button("➖ Remove Last") and len(st.session_state.fewshot) > 1:
#         st.session_state.fewshot.pop()

#     return st.session_state.fewshot