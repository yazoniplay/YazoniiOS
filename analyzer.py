import re

PAIN = ["i hate","frustrating","annoying","painful","tedious","manual","takes too long","waste time","struggle","hard to","difficult","broken","doesn't work","cant","can't","wish there was","looking for","need a tool","need an app","alternative","is there a way","how do i","any solution"]
BUYER = ["pay","paid","cost","expensive","subscription","customer","client","business","company","revenue","invoice","budget"]

def clean(text, limit=900):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit] + ("..." if len(text) > limit else "")

def analyze(title, body, comments=0, age_hours=0):
    text = f"{title} {body}".lower()
    pain = sum(x in text for x in PAIN)
    buyer = sum(x in text for x in BUYER)
    score = min(10, pain * 1.5 + buyer * 1.5 + (1 if len(body) >= 250 else 0) + (0.5 if comments >= 5 else 0) + (1 if age_hours <= 6 else 0))
    score = max(0, min(10, round(score)))
    if score < 4:
        return None
    customer = "People or businesses experiencing this problem"
    if any(x in text for x in ["server","minecraft","plugin","mod"]):
        customer = "Minecraft server owners / players"
    elif any(x in text for x in ["developer","coding","github","api"]):
        customer = "Developers / technical teams"
    elif any(x in text for x in ["shop","store","ecommerce","customer"]):
        customer = "Small businesses / online sellers"
    idea = "A simple tool that removes or automates the painful step"
    if "manual" in text or "takes too long" in text:
        idea = "Automation that turns the manual workflow into a one-click process"
    elif "alternative" in text or "expensive" in text:
        idea = "A cheaper, simpler alternative focused on the complained-about feature"
    return {"score": score, "problem": clean(body or title, 700), "title": clean(title, 180), "idea": idea, "customer": customer}
