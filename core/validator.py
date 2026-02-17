ALLOWED_CATEGORIES = {
    "none", "social", "governance", "environment",
    "social-governance", "environment-social",
    "environment-governance",
    "environment-social-governance"
}

ALLOWED_SENTIMENT = {"positive", "neutral", "negative", "none"}
ALLOWED_TONES = {"commitment", "action", "outcome", "none"}

def validate(item):

    if item["aspect_categories"] not in ALLOWED_CATEGORIES:
        item["aspect_categories"] = "none"

    if item["sentiment"] not in ALLOWED_SENTIMENT:
        item["sentiment"] = "none"

    if item["tones"] not in ALLOWED_TONES:
        item["tones"] = "none"

    item["confidence"] = float(item.get("confidence", 0))

    return item
