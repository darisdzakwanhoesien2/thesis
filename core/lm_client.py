import requests
import json

LM_URL = "http://localhost:1234/v1/chat/completions"
LM_MODEL = "local-model"

def call_lmstudio_batch(prompt):

    response = requests.post(
        LM_URL,
        json={
            "model": LM_MODEL,
            "messages": [
                {"role": "system", "content": "Strict ESG annotation engine."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 1000
        }
    )

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
