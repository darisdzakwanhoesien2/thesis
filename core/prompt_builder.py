def build_batch_prompt(samples):

    formatted = ""
    for i, s in enumerate(samples):
        formatted += f"""
ID: {s['id']}
Sentence: "{s['sentence_norm']}"
Aspect: "{s['canonical_aspect']}"
"""

    return f"""
You are an ESG annotation validator.

For EACH item below classify:

aspect_categories:
- none
- social
- governance
- environment
- social-governance
- environment-social
- environment-governance
- environment-social-governance

sentiment:
- positive
- neutral
- negative
- none

tones:
- commitment
- action
- outcome
- none

Also give:
confidence: float between 0 and 1
reasoning: short explanation

Return STRICT JSON LIST:

[
  {{
    "id": "...",
    "aspect_categories": "...",
    "sentiment": "...",
    "tones": "...",
    "confidence": 0.0,
    "reasoning": "..."
  }}
]

Items:
{formatted}
"""
