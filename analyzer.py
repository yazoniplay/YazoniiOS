import re

PAIN = [
    "i hate", "frustrating", "annoying", "painful", "tedious", "manual",
    "takes too long", "waste time", "struggle", "hard to", "difficult",
    "broken", "doesn't work", "cant", "can't", "wish there was",
    "looking for", "need a tool", "need an app", "alternative",
    "is there a way", "how do i", "any solution", "no way to"
]

BUYER = [
    "pay", "paid", "cost", "expensive", "subscription", "customer",
    "client", "business", "company", "revenue", "invoice", "budget",
    "pricing", "price", "money", "sales", "users"
]

GENERIC = [
    "apple", "iphone", "ios", "android", "google", "microsoft", "windows",
    "tesla", "elon musk", "stock market", "politics", "election", "president",
    "celebrity", "movie news", "game news", "review", "news", "launches",
    "announces", "acquires", "earnings", "security breach"
]

WEAK = [
    "what do you think", "unpopular opinion", "hot take", "thoughts?",
    "ama", "rant", "just curious", "interesting", "cool project",
    "showcase", "my project", "built this", "i made"
]

def clean(text, limit=900):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit] + ("..." if len(text) > limit else "")

def analyze(title, body, comments=0, age_hours=0):
    title = clean(title, 220)
    body = clean(body, 1400)
    text = f"{title} {body}".lower()

    if len(body.strip()) < 80:
        return None

    if any(x in text for x in GENERIC):
        return None

    if any(x in text for x in WEAK):
        return None

    pain_hits = [x for x in PAIN if x in text]
    buyer_hits = [x for x in BUYER if x in text]

    if len(pain_hits) < 2:
        return None

    if len(buyer_hits) < 1 and len(pain_hits) < 4:
        return None

    if len(body.split()) < 35 and len(pain_hits) < 3:
        return None

    score = 3.0
    score += min(3.0, len(pain_hits) * 0.75)
    score += min(2.0, len(buyer_hits) * 0.75)
    if comments >= 5:
        score += 0.5
    if comments >= 20:
        score += 0.5
    if age_hours <= 6:
        score += 0.5

    if any(x in text for x in [
        "i would pay", "take my money", "paid for", "paying for",
        "worth paying", "looking for a paid", "budget for"
    ]):
        score += 1.0

    score = max(0, min(10, round(score)))

    if score < 7:
        return None

    if any(x in text for x in ["server", "minecraft", "plugin", "mod"]):
        customer = "Minecraft server owners / players"
    elif any(x in text for x in ["developer", "coding", "github", "api", "software"]):
        customer = "Developers / technical teams"
    elif any(x in text for x in ["shop", "store", "ecommerce", "customer", "seller"]):
        customer = "Small businesses / online sellers"
    elif any(x in text for x in ["creator", "youtube", "tiktok", "stream", "content"]):
        customer = "Creators / content businesses"
    else:
        customer = "A specific niche experiencing this workflow problem"

    if any(x in text for x in ["manual", "takes too long", "tedious", "copy paste"]):
        idea = "Automate the repetitive workflow into a fast one-click process"
    elif any(x in text for x in ["alternative", "expensive", "subscription", "pricing"]):
        idea = "Build a focused, cheaper alternative around the missing feature"
    elif any(x in text for x in ["broken", "doesn't work", "can't", "cant"]):
        idea = "Build a reliable replacement that fixes the specific failure"
    else:
        idea = "Build a focused tool that directly solves the reported problem"

    return {
        "score": score,
        "problem": clean(body, 700),
        "title": clean(title, 180),
        "idea": idea,
        "customer": customer,
    }
