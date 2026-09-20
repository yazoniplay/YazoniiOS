import json,os,re,requests
URL="https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
SYSTEM="""You are YazoniiOS, a rigorous business-website opportunity analyst. Analyze only supplied evidence and never invent facts. Identify concrete commercially useful digital/website opportunities. Separate observation from inference. Return JSON only with name, category, summary, opportunity_score, confidence, pain_points, opportunities, recommended_action, evidence. Scores are 0-100. Opportunity score measures strength of observable opportunity; confidence measures evidence quality. Never recommend spam, deception, unauthorized access, or bypassing controls."""
def fallback(site,reason):return {"name":site.get("title") or site.get("domain"),"category":"unknown","summary":reason,"opportunity_score":0,"confidence":0,"pain_points":[],"opportunities":[],"recommended_action":"","evidence":[]}
def analyze(site):
 key=os.getenv("GEMINI_API_KEY")
 if not key:return fallback(site,"Gemini API key is not configured.")
 model=os.getenv("GEMINI_MODEL","gemini-3.6-flash")
 evidence={"domain":site["domain"],"url":site["url"],"search_query":site.get("query",""),"search_title":site.get("title",""),"search_description":site.get("description",""),"pages":[{"url":p["url"],"title":p["title"],"description":p["description"],"text":p["text"][:9000]} for p in site.get("pages",[])]}
 prompt="""Analyze this public website crawl as business intelligence. Look for evidence-backed conversion issues, unclear positioning, weak contact/booking paths, SEO/metadata gaps, thin or stale content, trust-signal gaps, technical inconsistencies, and automation opportunities. Do not claim something is missing unless the crawl supports it. EVIDENCE:\n"""+json.dumps(evidence,ensure_ascii=False)
 schema={"type":"object","properties":{"name":{"type":"string"},"category":{"type":"string"},"summary":{"type":"string"},"opportunity_score":{"type":"integer"},"confidence":{"type":"integer"},"pain_points":{"type":"array","items":{"type":"string"}},"opportunities":{"type":"array","items":{"type":"string"}},"recommended_action":{"type":"string"},"evidence":{"type":"array","items":{"type":"object","properties":{"signal":{"type":"string"},"observation":{"type":"string"},"implication":{"type":"string"}},"required":["signal","observation","implication"]}}},"required":["name","category","summary","opportunity_score","confidence","pain_points","opportunities","recommended_action","evidence"]}
 body={"system_instruction":{"parts":[{"text":SYSTEM}]},"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.2,"responseMimeType":"application/json","responseSchema":schema,"maxOutputTokens":1800}}
 r=requests.post(URL.format(model=model),headers={"x-goog-api-key":key,"Content-Type":"application/json"},json=body,timeout=45);r.raise_for_status();data=r.json();text=""
 for c in data.get("candidates",[]):
  for part in c.get("content",{}).get("parts",[]):
   if part.get("text"):text+=part["text"]
 try:return json.loads(text)
 except Exception:
  m=re.search(r"\{.*\}",text,re.S)
  return json.loads(m.group(0)) if m else fallback(site,"Gemini returned invalid JSON.")