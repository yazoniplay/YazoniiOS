import json
import logging
import os
from datetime import datetime, timezone

from analyzer import analyze
from crawler import crawl
from db import get_prospect, update_prospect, upsert_prospect
from discovery import discover
from discord import send_report

logger = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


def as_score(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def run_scan(queries):
    candidates = discover(
        queries, int(os.getenv("MAX_RESULTS_PER_QUERY", "20"))
    )
    analyzed = 0
    sent = 0
    errors = []

    for candidate in candidates:
        domain = candidate["domain"]
        upsert_prospect(
            domain,
            candidate["url"],
            candidate.get("title", ""),
            candidate.get("query", ""),
        )
        existing = get_prospect(domain)

        # Do not repeatedly crawl, analyze, and report prospects already sent.
        if existing and existing["discord_sent"] == 1:
            continue

        try:
            pages = crawl(candidate["url"])
            update_prospect(
                domain,
                last_crawled_at=now(),
                status="crawled",
            )
            result = analyze({**candidate, "pages": pages})
            score = as_score(result.get("opportunity_score"))
            confidence = as_score(result.get("confidence"))

            update_prospect(
                domain,
                name=result.get("name") or candidate.get("title") or domain,
                last_analyzed_at=now(),
                status="analyzed",
                opportunity_score=score,
                confidence=confidence,
                category=result.get("category", "unknown"),
                summary=result.get("summary", ""),
                pain_points="\n".join(result.get("pain_points") or []),
                opportunities="\n".join(result.get("opportunities") or []),
                recommended_action=result.get("recommended_action", ""),
                evidence=json.dumps(
                    result.get("evidence") or [], ensure_ascii=False
                ),
            )
            analyzed += 1

            report = {
                **result,
                "domain": domain,
                "url": candidate["url"],
                "opportunity_score": score,
                "confidence": confidence,
            }
            if send_report(report):
                update_prospect(
                    domain,
                    discord_sent=1,
                    status="reported",
                )
                sent += 1

        except Exception as error:
            logger.exception("Prospect processing failed: %s", domain)
            update_prospect(domain, status="error")
            errors.append(f"{domain}: {error}")

    return {
        "discovered": len(candidates),
        "analyzed": analyzed,
        "sent": sent,
        "errors": errors,
    }
