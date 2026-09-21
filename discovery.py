import logging
import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

class DiscoveryError(Exception):
    pass

LOGGER = logging.getLogger(__name__)

REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
SEARCH_ENDPOINTS = (
    "https://www.bing.com/search",
    "https://html.duckduckgo.com/html/",
    "https://lite.duckduckgo.com/lite/",
)

def _reddit_age_days():
    try:
        value = int(os.getenv("REDDIT_MAX_AGE_DAYS", "5"))
    except ValueError:
        value = 5
    return max(1, min(value, 5))

def _reddit_post_from_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    if host not in {"reddit.com", "old.reddit.com"}:
        return None

    path = parsed.path
    if not path.startswith(("/r/", "/comments/")):
        return None

    if "/comments/" in path:
        post_id = path.split("/comments/", 1)[1].split("/", 1)[0]
    else:
        parts = [part for part in path.split("/") if part]
        post_id = parts[-1] if parts else ""

    if not post_id:
        return None

    return f"reddit:{post_id}"

def _clean_search_url(href):
    if not href:
        return ""

    parsed = urlparse(href)

    # Bing/DuckDuckGo sometimes wrap the destination in a redirect URL.
    if parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            return unquote(target)

    target = parse_qs(parsed.query).get("url", [None])[0]
    if target and "bing.com" in (parsed.hostname or ""):
        return unquote(target)

    return href

def _search_engine_candidates(session, query, per_query, seen):
    cutoff_date = (
        datetime.now(timezone.utc) - timedelta(days=_reddit_age_days())
    ).date()

    search_query = (
        f'site:reddit.com ("{query}") after:{cutoff_date.isoformat()}'
    )

    for endpoint in SEARCH_ENDPOINTS:
        try:
            response = session.get(
                endpoint,
                params={
                    "q": search_query,
                    "count": min(per_query, 50),
                    "num": min(per_query, 50),
                    "kl": "wt-wt",
                },
                timeout=15,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Bing uses li.b_algo. DuckDuckGo uses .result.
            results = soup.select("li.b_algo")
            if not results:
                results = soup.select(".result")
            if not results:
                results = soup.select("div[data-testid='result']")

            found = []

            for result in results:
                if len(found) >= per_query:
                    break

                anchor = (
                    result.select_one("h2 a")
                    or result.select_one("a.result__a")
                    or result.select_one("a[data-testid='result-title-a']")
                )
                if not anchor:
                    continue

                href = _clean_search_url(anchor.get("href"))
                post_id = _reddit_post_from_url(href)
                if not post_id or post_id in seen:
                    continue

                snippet = (
                    result.select_one(".b_caption p")
                    or result.select_one(".result__snippet")
                    or result.select_one("p")
                )

                seen.add(post_id)
                found.append({
                    "url": href,
                    "domain": post_id,
                    "title": anchor.get_text(" ", strip=True) or "Reddit discussion",
                    "description": (
                        snippet.get_text(" ", strip=True)[:3000]
                        if snippet else ""
                    ),
                    "query": query,
                    "source": "reddit",
                    "subreddit": "",
                })

            if found:
                LOGGER.info(
                    "Search-engine Reddit fallback: endpoint=%s query=%r results=%s",
                    endpoint,
                    query,
                    len(found),
                )
                return found

        except requests.RequestException as exc:
            LOGGER.warning(
                "Search-engine Reddit fallback failed: endpoint=%s query=%r error=%s",
                endpoint,
                query,
                exc,
            )

    return []

def _reddit_candidates(session, query, per_query, seen):
    cutoff = (
        datetime.now(timezone.utc).timestamp()
        - (_reddit_age_days() * 86400)
    )

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
                "User-Agent": "YazoniiOS/1.3 Reddit prospect discovery",
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.info(
            "Direct Reddit API unavailable for %r; using search fallback: %s",
            query,
            exc,
        )
        return _search_engine_candidates(session, query, per_query, seen)

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
    """Discover Reddit posts only. Search engines are used only to locate Reddit URLs."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "YazoniiOS/1.3 Reddit prospect discovery",
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
        LOGGER.info(
            "Reddit discovery: query=%r results=%s",
            query,
            len(results),
        )

        if index < len(queries) - 1:
            time.sleep(1)

    LOGGER.info(
        "Reddit-only discovery complete: queries=%s total=%s",
        len(queries),
        len(found),
    )
    return found
