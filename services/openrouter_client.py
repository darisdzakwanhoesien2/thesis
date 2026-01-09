import os
import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(messages, model, temperature=0.3, max_tokens=1024):

    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not found in environment variables.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "ABSA PDF Playground",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code} Error: {response.text}")

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        raise RuntimeError(f"Unexpected response format: {data}")


# import os
# import requests

# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# def call_openrouter(messages, model, temperature=0.7, max_tokens=1024):
#     api_key = os.getenv("OPENROUTER_API_KEY")
#     if not api_key:
#         raise RuntimeError("OPENROUTER_API_KEY not found.")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": "http://localhost:8501",
#         "X-Title": "ABSA Playground",
#     }

#     payload = {
#         "model": model,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#         "stream": False,
#     }

#     r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
#     r.raise_for_status()
#     data = r.json()

#     choice = data["choices"][0]

#     # Standard OpenAI style
#     if "message" in choice and "content" in choice["message"]:
#         content = choice["message"]["content"]

#         if isinstance(content, list):
#             texts = []
#             for part in content:
#                 if isinstance(part, dict) and "text" in part:
#                     texts.append(part["text"])
#             return "\n".join(texts)

#         return content

#     # Fallback
#     return str(data)


# import os
# import requests

# OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# def call_openrouter(messages, model, temperature=0.7, max_tokens=1024):
#     api_key = os.getenv("OPENROUTER_API_KEY")

#     if not api_key:
#         raise RuntimeError("OPENROUTER_API_KEY not found in environment.")

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json",
#         "HTTP-Referer": "http://localhost:8501",
#         "X-Title": "Streamlit LLM Playground",
#     }

#     payload = {
#         "model": model,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens,
#     }

#     r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
#     r.raise_for_status()
#     return r.json()["choices"][0]["message"]["content"]


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