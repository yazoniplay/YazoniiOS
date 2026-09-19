import aiohttp
from datetime import datetime, timezone
from analyzer import analyze
from database import seen

SUBS = ["Entrepreneur","smallbusiness","SaaS","SideProject","startups","webdev"]

async def reddit(session):
    out = []
    headers = {"User-Agent":"OpportunityScout/5.0"}
    for sub in SUBS:
        try:
            async with session.get(f"https://www.reddit.com/r/{sub}/new.json?limit=40", headers=headers, timeout=15) as r:
                if r.status != 200:
                    print("Reddit", sub, "HTTP", r.status); continue
                data = await r.json()
                for x in data.get("data",{}).get("children",[]):
                    p=x.get("data",{}); pid="reddit:"+str(p.get("id"))
                    if await seen(pid): continue
                    age=(datetime.now(timezone.utc).timestamp()-p.get("created_utc",datetime.now(timezone.utc).timestamp()))/3600
                    a=analyze(p.get("title",""),p.get("selftext",""),p.get("num_comments",0),age)
                    if a:
                        a.update(id=pid,url="https://reddit.com"+p.get("permalink",""),source=f"Reddit r/{sub}")
                        out.append(a)
        except Exception as e: print("Reddit error:",e)
    return out

async def hackernews(session):
    out=[]
    for q in ["need a tool","looking for software","frustrating","manual workflow","alternative"]:
        try:
            async with session.get("https://hn.algolia.com/api/v1/search_by_date",params={"query":q,"tags":"story","hitsPerPage":20},timeout=15) as r:
                if r.status != 200: continue
                for p in (await r.json()).get("hits",[]):
                    pid="hn:"+str(p.get("objectID"))
                    if await seen(pid): continue
                    a=analyze(p.get("title",""),p.get("story_text") or "",p.get("num_comments",0),1)
                    if a:
                        a.update(id=pid,url=p.get("url") or f"https://news.ycombinator.com/item?id={p.get('objectID')}",source="Hacker News")
                        out.append(a)
        except Exception as e: print("HN error:",e)
    return out

async def github_issues(session):
    out=[]; headers={"Accept":"application/vnd.github+json","User-Agent":"OpportunityScout/5.0"}
    for q in ['"please add" in:title','"feature request" in:title','"wish" in:title','"manual" in:title','"does not work" in:title']:
        try:
            params={"q":f"{q} is:issue is:open created:>=2026-09-18","sort":"created","order":"desc","per_page":20}
            async with session.get("https://api.github.com/search/issues",params=params,headers=headers,timeout=15) as r:
                if r.status != 200: print("GitHub HTTP",r.status); continue
                for p in (await r.json()).get("items",[]):
                    pid="github:"+str(p.get("id"))
                    if await seen(pid): continue
                    a=analyze(p.get("title",""),p.get("body") or "",p.get("comments",0),1)
                    if a:
                        a.update(id=pid,url=p.get("html_url",""),source="GitHub Issues")
                        out.append(a)
        except Exception as e: print("GitHub error:",e)
    unique={}
    for x in out:
        k=x["title"].lower()
        if k not in unique or x["score"] > unique[k]["score"]: unique[k]=x
    return sorted(unique.values(), key=lambda x:x["score"], reverse=True)[:10]

async def scan_opportunities():
    async with aiohttp.ClientSession() as session:
        results = []
        results += await reddit(session)
        results += await hackernews(session)
        results += await github_issues(session)
    return sorted(results, key=lambda x:x["score"], reverse=True)[:10]
