import logging
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

class DiscoveryError(Exception):
    pass

LOGGER = logging.getLogger(__name__)

SUBREDDITS = (
    "forhire",
    "web_design",
    "webdev",
    "smallbusiness",
    "Entrepreneur",
    "startups",
    "shopify",
    "ecommerce",
    "Wordpress",
)

INTENT_TERMS = (
    "need a website",
    "need website",
    "looking for a web designer",
    "looking for a web developer",
    "looking for a website",
    "need a web developer",
    "need a website developer",
    "website redesign",
    "redesign my website",
    "website is outdated",
    "website not mobile friendly",
    "need help with my website",
    "help with my website",
    "build a website",
    "build me a website",
    "create a website",
    "make me a website",
    "new website",
    "website project",
    "shopify website",
    "ecommerce website",
    "online store",
)

OFFER_TERMS = (
    "[for hire]",
    "for hire",
    "i will build",
    "i can build",
    "i build websites",
    "offering web",
    "web developer here",
    "web designer here",
)

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

def _post_age_ok(created):
    cutoff = datetime.now(timezone.utc).timestamp() - (_reddit_age_days() * 86400)
    return float(created or 0) >= cutoff

def _reddit_post_from_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"reddit.com", "old.reddit.com"}:
        return None
    path = parsed.path
    if "/comments/" not in path:
        return None
    post_id = path.split("/comments/", 1)[1].split("/", 1)[0]
    return f"reddit:{post_id}" if post_id else None

def _clean_text(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)

def _is_relevant(title, body, query=""):
    text = f"{title} {body}".lower()
    query_words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]

    if any(term in text for term in OFFER_TERMS):
        return False

    if any(term in text for term in INTENT_TERMS):
        return True

    # Also accept posts containing several website-related terms.
    website_words = sum(
        word in text
        for word in ("website", "web", "shopify", "ecommerce", "wordpress", "online store")
    )
    request_words = sum(
        word in text
        for word in ("need", "looking", "help", "want", "hire", "hiring", "build", "create", "redesign", "developer", "designer")
    )
    query_match = sum(word in text for word in query_words) >= min(2, len(query_words))

    return website_words >= 1 and request_words >= 2 and query_match

def _reddit_new_candidates(session, subreddit, per_subreddit, seen, queries):
    url = f"https://www.reddit.com/r/{subreddit}/new.json"
    try:
        response = session.get(
            url,
            params={"limit": 100, "raw_json": 1},
            headers={"Accept": "application/json"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Reddit subreddit fetch failed: r/%s error=%s", subreddit, exc)
        return []

    found = []
    for child in payload.get("data", {}).get("children", []):
        data = child.get("data") or {}
        created = float(data.get("created_utc") or 0)
        title = data.get("title") or ""
        body = _clean_text(data.get("selftext") or "")
        permalink = data.get("permalink")
        post_id = data.get("id")

        if not post_id or not permalink or not _post_age_ok(created):
            continue

        query = next(
            (q for q in queries if _is_relevant(title, body, q)),
            "",
        )
        if not query:
            continue

        domain = f"reddit:{post_id}"
        if domain in seen:
            continue

        seen.add(domain)
        found.append({
            "url": "https://www.reddit.com" + permalink,
            "domain": domain,
            "title": title[:300],
            "description": body[:3000],
            "query": query,
            "source": "reddit",
            "subreddit": subreddit,
            "created_utc": created,
        })

        if len(found) >= per_subreddit:
            break

    return found

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
                params={"q": search_query, "count": 50, "num": 50, "kl": "wt-wt"},
                timeout=15,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.select("li.b_algo") or soup.select(".result") or soup.select("div[data-testid='result']")
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

                href = anchor.get("href") or ""
                parsed = urlparse(href)
                if parsed.path.startswith("/l/"):
                    target = parse_qs(parsed.query).get("uddg", [None])[0]
                    if target:
                        href = unquote(target)

                post_id = _reddit_post_from_url(href)
                if not post_id or post_id in seen:
                    continue

                snippet = result.select_one(".b_caption p") or result.select_one(".result__snippet") or result.select_one("p")
                description = snippet.get_text(" ", strip=True)[:3000] if snippet else ""
                title = anchor.get_text(" ", strip=True)

                if not _is_relevant(title, description, query):
                    continue

                seen.add(post_id)
                found.append({
                    "url": href,
                    "domain": post_id,
                    "title": title[:300],
                    "description": description,
                    "query": query,
                    "source": "reddit",
                    "subreddit": "",
                })

            if found:
                return found

        except requests.RequestException as exc:
            LOGGER.warning("Search fallback failed: %s query=%r error=%s", endpoint, query, exc)

    return []

def discover(queries, count=20):
    """Reddit-only discovery using subreddit feeds first, then search engines."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "YazoniiOS/1.4 prospect discovery by yazonii",
        "Accept-Language": "en-US,en;q=0.9",
    })

    found = []
    seen = set()
    per_subreddit = max(2, min(int(count), 20))

    # Do not rely on Reddit's search endpoint. Read recent posts from relevant
    # subreddits and filter them locally; this still returns Reddit posts only.
    for subreddit in SUBREDDITS:
        results = _reddit_new_candidates(
            session, subreddit, per_subreddit, seen, queries
        )
        found.extend(results)
        LOGGER.info(
            "Reddit subreddit discovery: r/%s results=%s",
            subreddit,
            len(results),
        )
        time.sleep(0.5)

    # Search engines are a secondary source only. They are strictly filtered
    # so non-Reddit pages can never become prospects.
    if len(found) < max(5, min(int(count), 20)):
        for query in queries:
            query = str(query).strip()
            if not query:
                continue
            results = _search_engine_candidates(session, query, count, seen)
            found.extend(results)
            LOGGER.info("Reddit search fallback: query=%r results=%s", query, len(results))
            time.sleep(0.5)

    LOGGER.info(
        "Reddit-only discovery complete: subreddits=%s queries=%s total=%s",
        len(SUBREDDITS),
        len(queries),
        len(found),
    )
    return found
