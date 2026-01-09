import os
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(messages, model, temperature=0.7, max_tokens=1024):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not found in environment.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Streamlit LLM Playground",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


# import os
# import requests

# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# def call_openrouter(messages, model, temperature=0.7, max_tokens=512):
#     api_key = os.getenv("OPENROUTER_API_KEY")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": "http://localhost:8501",
#         "X-Title": "Streamlit LLM Playground"
#     }

#     payload = {
#         "model": model,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#     }

#     r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
#     r.raise_for_status()
#     return r.json()["choices"][0]["message"]["content"]