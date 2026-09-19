import re

PROBLEM = [
    "i hate", "i'm frustrated", "im frustrated", "frustrating", "annoying",
    "painful", "tedious", "manual", "takes too long", "waste time",
    "wasting time", "struggle", "can't figure out", "cant figure out",
    "doesn't work", "doesnt work", "broken", "keeps failing",
    "wish there was", "need a tool", "need an app", "looking for a tool",
    "looking for an app", "is there a way", "any solution", "no way to",
    "hard to", "difficult to"
]

SOLUTION_REQUEST = [
    "how do i", "how can i", "is there a tool", "is there an app",
    "what tool", "what app", "any tool", "any app", "alternative to",
    "looking for", "need a tool", "need an app", "recommend a", "recommendation"
]

PAYMENT = [
    "i would pay", "i'd pay", "willing to pay", "happy to pay",
    "take my money", "paying for", "paid for", "pay for",
    "worth paying", "budget for", "subscription", "too expensive",
    "expensive", "pricing", "price"
]

# Hard reject product launches/showcases. These are NOT opportunity reports.
ANNOUNCEMENT_PATTERNS = [
    r"^show\s+hn\s*:",
    r"^show\s+hacker\s+news\s*:",
    r"^i\s+(built|made|created|launched)\b",
    r"^introducing\b",
    r"^launching\b",
    r"^built\s+this\b",
    r"^my\s+project\b",
    r"^open[- ]source\s+(platform|tool|app|project)\b",
    r"^demo\s*:",
    r"^\[?showcase\]?",
]

GENERIC = [
    "apple", "iphone", "ios", "android", "google", "microsoft", "windows",
    "tesla", "elon musk", "stock market", "politics", "election", "president",
    "celebrity", "movie news", "game news", "review", "news", "launches",
    "announces", "acquires", "earnings", "security breach"
]

WEAK = [
    "what do you think", "unpopular opinion", "hot take", "thoughts?",
    "ama", "rant", "just curious", "cool project", "showcase",
    "my project", "built this", "i made", "look what i made"
]

def clean(text, limit=900):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit] + ("..." if len(text) > limit else "")

def analyze(title, body, comments=0, age_hours=0):
    title = clean(title, 220)
    body = clean(body, 1400)
    text = f"{title} {body}".lower()

    # Announcement/project posts are never opportunity signals.
    if any(re.search(p, title.lower()) for p in ANNOUNCEMENT_PATTERNS):
        return None

    if len(body.split()) < 45:
        return None

    if any(x in text for x in GENERIC) or any(x in text for x in WEAK):
        return None

    problem_hits = [x for x in PROBLEM if x in text]
    solution_hits = [x for x in SOLUTION_REQUEST if x in text]
    payment_hits = [x for x in PAYMENT if x in text]

    if not problem_hits or not solution_hits:
        return None

    if len(problem_hits) < 2 and not payment_hits:
        return None

    score = 5
    score += min(2, len(problem_hits))
    score += min(2, len(solution_hits))
    if payment_hits:
        score += 2
    if comments >= 10:
        score += 1
    if comments >= 30:
        score += 1
    if age_hours <= 6:
        score += 1

    score = min(10, score)

    if not payment_hits:
        score = min(score, 8)

    if score < 7:
        return None

    if any(x in text for x in ["server", "minecraft", "plugin", "mod"]):
        customer = "Minecraft server owners / players"
    elif any(x in text for x in ["developer", "coding", "github", "api", "software"]):
        customer = "Developers / technical teams"
    elif any(x in text for x in ["shop", "store", "ecommerce", "seller"]):
        customer = "Small businesses / online sellers"
    elif any(x in text for x in ["creator", "youtube", "tiktok", "stream", "content"]):
        customer = "Creators / content businesses"
    else:
        customer = "Niche users with this specific workflow problem"

    if any(x in text for x in ["manual", "takes too long", "tedious", "waste time"]):
        idea = "Automate the exact repetitive workflow"
    elif any(x in text for x in ["alternative", "too expensive", "pricing", "subscription"]):
        idea = "Build a focused alternative with the missing/cheaper capability"
    else:
        idea = "Build a focused tool that directly solves the requested problem"

    return {
        "score": score,
        "problem": clean(body, 700),
        "title": clean(title, 180),
        "idea": idea,
        "customer": customer,
    }
