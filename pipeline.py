import os
from datetime import datetime, timezone

from analyzer import analyze
from crawler import crawl
from db import upsert_prospect, update_prospect
from discovery import discover
from discord import send_report

def now():
    return datetime.now(timezone.utc).isoformat()

def run_scan(queries):
    max_results=int(os.getenv("MAX_RESULTS_PER_QUERY","20"))
    candidates=discover(queries,max_results)
    analyzed=0; sent=0; errors=[]
    for c in candidates:
        row=upsert_prospect(c["domain"],c["url"],c.get("title",""),c.get("query",""))
        try:
            pages=crawl(c["url"])
            update_prospect(c["domain"],last_crawled_at=now(),status="crawled")
            site={**c,"pages":pages}
            result=analyze(site)
            score=max(0,min(100,int(result.get("opportunity_score",0))))
            confidence=max(0,min(100,int(result.get("confidence",0))))
            update_prospect(
                c["domain"],
                name=result.get("name") or c.get("title") or c["domain"],
                last_analyzed_at=now(),status="analyzed",
                opportunity_score=score,confidence=confidence,
                category=result.get("category","unknown"),
                summary=result.get("summary",""),
                pain_points="\n".join(result.get("pain_points") or []),
                opportunities="\n".join(result.get("opportunities") or []),
                recommended_action=result.get("recommended_action",""),
                evidence=__import__("json").dumps(result.get("evidence") or [],ensure_ascii=False),
            )
            analyzed += 1
            discord_payload={**result,"domain":c["domain"],"url":c["url"]}
            try:
                if send_report(discord_payload):
                    update_prospect(c["domain"],discord_sent=1,status="reported")
                    sent += 1
            except Exception as e:
                errors.append(f"Discord {c['domain']}: {e}")
        except Exception as e:
            update_prospect(c["domain"],status="error")
            errors.append(f"{c['domain']}: {e}")
    return {"discovered":len(candidates),"analyzed":analyzed,"sent":sent,"errors":errors}
