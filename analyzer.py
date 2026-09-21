import json
import os
import re
import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
SYSTEM = """You are YazoniiOS, a rigorous business-website opportunity analyst. Analyze only supplied public evidence and never invent facts. Identify concrete website opportunities and create a respectful, personalized outreach pitch that the user can manually adapt. Never recommend spam, deception, impersonation, unauthorized access, or bypassing controls. Return JSON only."""


def fallback(site, reason):
    return {
        "name": site.get("title") or site.get("domain"),
        "category": "unknown",
        "summary": reason,
        "opportunity_score": 0,
        "confidence": 0,
        "pain_points": [],
        "opportunities": [],
        "recommended_action": "",
        "pitch_subject": "",
        "pitch": "",
        "pitch_notes": [],
        "evidence": [],
    }


def analyze(site):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return fallback(site, "Gemini API key is not configured.")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    evidence = {
        "domain": site["domain"],
        "url": site["url"],
        "search_query": site.get("query", ""),
        "search_title": site.get("title", ""),
        "search_description": site.get("description", ""),
        "pages": [
            {
                "url": p["url"],
                "title": p["title"],
                "description": p["description"],
                "text": p["text"][:9000],
            }
            for p in site.get("pages", [])
        ],
    }
    prompt = """Analyze this public website crawl as business intelligence. Look for evidence-backed conversion issues, unclear positioning, weak contact or booking paths, SEO and metadata gaps, thin or stale content, trust-signal gaps, and useful redesign opportunities. Do not claim something is missing unless the crawl supports it.

Create a short, human-sounding outreach pitch. It must mention one or two real observations from the evidence, avoid exaggerated claims, avoid pretending to have tested anything that was not tested, and be framed as a suggestion the user can manually personalize. Do not use aggressive sales language.

EVIDENCE:\n""" + json.dumps(evidence, ensure_ascii=False)
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "category": {"type": "string"},
            "summary": {"type": "string"},
            "opportunity_score": {"type": "integer"},
            "confidence": {"type": "integer"},
            "pain_points": {"type": "array", "items": {"type": "string"}},
            "opportunities": {"type": "array", "items": {"type": "string"}},
            "recommended_action": {"type": "string"},
            "pitch_subject": {"type": "string"},
            "pitch": {"type": "string"},
            "pitch_notes": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "object", "properties": {"signal": {"type": "string"}, "observation": {"type": "string"}, "implication": {"type": "string"}}, "required": ["signal", "observation", "implication"]}},
        },
        "required": ["name", "category", "summary", "opportunity_score", "confidence", "pain_points", "opportunities", "recommended_action", "pitch_subject", "pitch", "pitch_notes", "evidence"],
    }
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.25, "responseMimeType": "application/json", "responseSchema": schema, "maxOutputTokens": 2600},
    }
    response = requests.post(URL.format(model=model), headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=body, timeout=45)
    response.raise_for_status()
    data = response.json()
    text = ""
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if part.get("text"):
                text += part["text"]
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.S)
        return json.loads(match.group(0)) if match else fallback(site, "Gemini returned invalid JSON.")
