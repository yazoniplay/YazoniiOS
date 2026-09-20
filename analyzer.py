import json, os, re, requests

GEMINI_URL="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = """You are YazoniiOS, a rigorous business-website opportunity analyst.
Analyze only the evidence supplied in the request. Never invent facts.
Your job is to identify concrete, commercially useful website/digital opportunities
for the business. Separate observed evidence from inference.
Return JSON only with these fields:
name, category, summary, opportunity_score, confidence,
pain_points (array of strings), opportunities (array of strings),
recommended_action, evidence (array of objects with signal, observation, implication).
Scores are 0-100. Opportunity score is about the strength of observable opportunity,
not the quality of the business. Confidence is about evidence quality.
Do not recommend spam, deceptive practices, or unauthorized access."""

def _fallback(payload, reason):
    return {
        "name":payload.get("title") or payload.get("domain"),
        "category":"unknown","summary":reason,
        "opportunity_score":0,"confidence":0,
        "pain_points":[],"opportunities":[],"recommended_action":"",
        "evidence":[]
    }

def analyze(site):
    key=os.getenv("GEMINI_API_KEY")
    if not key: return _fallback(site,"Gemini API key is not configured.")
    model=os.getenv("GEMINI_MODEL","gemini-3.6-flash")
    evidence={
        "domain":site["domain"],"url":site["url"],
        "search_query":site.get("query",""),
        "search_title":site.get("title",""),
        "search_description":site.get("description",""),
        "pages":[{
            "url":p["url"],"title":p["title"],"description":p["description"],
            "text":p["text"][:9000]
        } for p in site.get("pages",[])]
    }
    prompt="""Analyze this public website crawl as business intelligence.
Look specifically for missing or weak conversion paths, unclear positioning,
mobile/usability clues, missing contact/booking flows, weak metadata/SEO,
stale or thin content, trust-signal gaps, technical inconsistencies, and
obvious automation opportunities. Do not claim something is missing unless
the crawl evidence supports it.

EVIDENCE:
""" + json.dumps(evidence,ensure_ascii=False)
    schema={
        "type":"object","properties":{
            "name":{"type":"string"},"category":{"type":"string"},"summary":{"type":"string"},
            "opportunity_score":{"type":"integer"},"confidence":{"type":"integer"},
            "pain_points":{"type":"array","items":{"type":"string"}},
            "opportunities":{"type":"array","items":{"type":"string"}},
            "recommended_action":{"type":"string"},
            "evidence":{"type":"array","items":{"type":"object","properties":{
                "signal":{"type":"string"},"observation":{"type":"string"},"implication":{"type":"string"}
            },"required":["signal","observation","implication"]}}
        },
        "required":["name","category","summary","opportunity_score","confidence","pain_points","opportunities","recommended_action","evidence"]
    }
    body={
        "system_instruction":{"parts":[{"text":SYSTEM}]},
        "contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{"temperature":0.2,"responseMimeType":"application/json","responseSchema":schema,"maxOutputTokens":1800}
    }
    r=requests.post(GEMINI_URL.format(model=model),headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=body,timeout=45)
    r.raise_for_status()
    data=r.json()
    text=""
    for c in data.get("candidates",[]):
        for part in c.get("content",{}).get("parts",[]):
            if part.get("text"): text += part["text"]
    try:
        parsed=json.loads(text)
    except Exception:
        match=re.search(r"\{.*\}",text,re.S)
        parsed=json.loads(match.group(0)) if match else _fallback(site,"Gemini returned invalid JSON.")
    return parsed
