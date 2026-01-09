You are an expert ESG analyst performing Aspect-Based Sentiment Analysis (ABSA) on corporate sustainability disclosures.

Analyze the following text and extract all ESG-relevant statements.

For each identified statement, produce a JSON object containing:

---

## Core ABSA

* sentence
* aspect
* aspect_category ("E", "S", or "G")
* ontology_uri
* sentiment ("positive", "neutral", "negative")
* sentiment_score (continuous, model-generated, ranging from –1 to +1)

  * Negative range: –1.0 to –0.2
  * Neutral range: –0.2 to +0.2
  * Positive range: +0.2 to +1.0

* tone ("Commitment", "Action", "Outcome")
* confidence (0–1)

## Extended ESG Intelligence Fields

* materiality ("high", "medium", "low")
* claim_type ("quantitative" or "qualitative")
* has_kpi (true/false)
* time_horizon ("past", "present", "future")
* has_target (true/false)
* target_type ("absolute", "intensity", "science-based", or null)
* emission_scope ("Scope 1", "Scope 2", "Scope 3", "multiple", or null)
* stakeholder ("employees", "communities", "suppliers", "customers", "environment", etc.)
* esg_risk_type ("risk", "opportunity", or null)
* impact_level ("low", "moderate", "high")
* externally_assured (true/false)
* value_chain_stage ("operations", "supply_chain", "downstream", "full_lifecycle")
* policy_reference (true/false)
* partner_type ("NGO", "government", "industry", "none")
* regulation_uri (e.g., "CSRD", "TCFD", "EU Taxonomy", "ISSB", "SDG13", or null)

## JSON Reasoning Requirement

Include a reasoning field inside the JSON object containing:

* why the aspect was selected
* why the aspect_category (E/S/G) was chosen
* why the ontology_uri fits
* why sentiment is positive/neutral/negative
* why the sentiment_score falls in that position
* why the tone is Commitment/Action/Outcome
* any key cues affecting confidence

This reasoning must be concise, factual, and tied directly to the text

## Output Requirements

* Return a valid JSON array only
* No explanation outside the JSON
* Each ESG-related statement becomes one JSON object
