import logging
import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

class DiscoveryError(Exception):
    pass

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
LOGGER = logging.getLogger(__name__)

def _reddit_age_days():
    try:
        value = int(os.getenv("REDDIT_MAX_AGE_DAYS", "5"))
    except ValueError:
        value = 5
    return max(1, min(value, 5))

def _reddit_candidates_from_search(session, query, per_query, seen):
    """Fallback when Reddit blocks direct API requests in GitHub Actions."""
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=_reddit_age_days())).date()
    search_query = f"site:reddit.com {query} after:{cutoff_date.isoformat()}"

    # Use a search engine only to locate Reddit posts. Never return non-Reddit results.
    for endpoint in ("https://html.duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"):
        try:
            response = session.get(
                endpoint,
                params={"q": search_query, "kl": "wt-wt"},
                timeout=15,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.select(".result") or soup.select("div[data-testid='result']")
            found = []

            for result in results:
                if len(found) >= per_query:
                    break

                anchor = result.select_one("a.result__a") or result.select_one(
                    "a[data-testid='result-title-a']"
                )
                if not anchor:
                    continue

                href = anchor.get("href")
                if not href:
                    continue

                parsed = urlparse(href)
                if parsed.path.startswith("/l/"):
                    from urllib.parse import parse_qs, unquote
                    target = parse_qs(parsed.query).get("uddg", [None])[0]
                    if target:
                        href = unquote(target)
                        parsed = urlparse(href)

                host = (parsed.hostname or "").lower()
                if host.startswith("www."):
                    host = host[4:]

                if host not in {"reddit.com", "old.reddit.com"}:
                    continue
                if not parsed.path.startswith(("/r/", "/comments/")):
                    continue

                post_match = parsed.path.split("/comments/")
                post_id = post_match[1].split("/")[0] if len(post_match) == 2 else parsed.path
                domain = f"reddit:{post_id}"

                if domain in seen:
                    continue

                snippet = result.select_one(".result__snippet")
                seen.add(domain)
                found.append({
                    "url": href,
                    "domain": domain,
                    "title": anchor.get_text(" ", strip=True) or "Reddit discussion",
                    "description": snippet.get_text(" ", strip=True)[:3000] if snippet else "",
                    "query": query,
                    "source": "reddit",
                    "subreddit": "",
                })

            if found:
                return found
        except requests.RequestException as exc:
            LOGGER.warning("Reddit search fallback failed for %r: %s", query, exc)

    return []

def _reddit_candidates(session, query, per_query, seen):
    cutoff = datetime.now(timezone.utc).timestamp() - (_reddit_age_days() * 86400)

    try:
        response = session.get(
            REDDIT_SEARCH_URL,
            params={
                "q": query,
                "sort": "new",
                "t": "week",
                "limit": per_query,
                "raw_json": 1,
            },
            headers={
                "Accept": "application/json",
                "User-Agent": "YazoniiOS/1.2 Reddit prospect discovery",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return _reddit_candidates_from_search(session, query, per_query, seen)

    found = []
    for child in payload.get("data", {}).get("children", []):
        data = child.get("data") or {}
        created = float(data.get("created_utc") or 0)
        permalink = data.get("permalink")
        post_id = data.get("id")

        if not permalink or not post_id or created < cutoff:
            continue

        domain = f"reddit:{post_id}"
        if domain in seen:
            continue

        seen.add(domain)
        found.append({
            "url": "https://www.reddit.com" + permalink,
            "domain": domain,
            "title": data.get("title") or "Reddit discussion",
            "description": BeautifulSoup(
                data.get("selftext") or "", "html.parser"
            ).get_text(" ", strip=True)[:3000],
            "query": query,
            "source": "reddit",
            "subreddit": data.get("subreddit", ""),
            "created_utc": created,
        })

    return found

def discover(queries, count=20):
    """Reddit-only prospect discovery. Web search is used only as a Reddit fallback."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "YazoniiOS/1.2 Reddit prospect discovery",
        "Accept-Language": "en-US,en;q=0.8",
    })

    found = []
    seen = set()
    per_query = max(1, min(int(count), 50))

    for index, raw_query in enumerate(queries):
        query = str(raw_query).strip()
        if not query:
            continue

        results = _reddit_candidates(session, query, per_query, seen)
        found.extend(results)
        LOGGER.info("Reddit discovery: query=%r results=%s", query, len(results))

        if index < len(queries) - 1:
            time.sleep(1)

    LOGGER.info("Reddit-only discovery complete: queries=%s total=%s", len(queries), len(found))
    return found
