import aiohttp
from datetime import datetime, timezone
from analyzer import analyze
from database import seen

SUBS = ["Entrepreneur", "smallbusiness", "SaaS", "SideProject", "startups", "webdev"]

async def reddit(session):
    out = []
    headers = {"User-Agent": "OpportunityScout/6.0"}
    for sub in SUBS:
        try:
            async with session.get(f"https://www.reddit.com/r/{sub}/new.json?limit=50", headers=headers, timeout=15) as r:
                if r.status != 200:
                    print("Reddit", sub, "HTTP", r.status)
                    continue
                data = await r.json()
                for x in data.get("data", {}).get("children", []):
                    p = x.get("data", {})
                    pid = "reddit:" + str(p.get("id"))
                    if await seen(pid):
                        continue
                    age = (datetime.now(timezone.utc).timestamp() - p.get("created_utc", datetime.now(timezone.utc).timestamp())) / 3600
                    a = analyze(p.get("title", ""), p.get("selftext", ""), p.get("num_comments", 0), age)
                    if a:
                        a.update(
                            id=pid,
                            url="https://reddit.com" + p.get("permalink", ""),
                            source=f"Reddit r/{sub}",
                        )
                        out.append(a)
        except Exception as e:
            print("Reddit error:", e)
    return out

async def hackernews(session):
    # HN is intentionally disabled for now. It produces too much general
    # tech/news content for this use case.
    return []

async def github_issues(session):
    # GitHub feature requests are useful for developer research, but usually
    # describe improvements to an existing project rather than a standalone
    # business opportunity. Keep them out of the opportunity feed for now.
    return []

async def scan_opportunities():
    async with aiohttp.ClientSession() as session:
        results = await reddit(session)
    return sorted(results, key=lambda x: x["score"], reverse=True)[:3]
