import logging
import os
import re
import time
import xml.etree.ElementTree as ET
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
    "need a website", "need website", "looking for a web designer",
    "looking for a web developer", "looking for a website",
    "need a web developer", "need a website developer", "website redesign",
    "redesign my website", "website is outdated", "website not mobile friendly",
    "need help with my website", "help with my website", "build a website",
    "build me a website", "create a website", "make me a website",
    "new website", "website project", "shopify website",
    "ecommerce website", "online store",
)

OFFER_TERMS = (
    "[for hire]", "for hire", "i will build", "i can build",
    "i build websites", "offering web", "web developer here",
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

def _parse_reddit_date(value):
    if not value:
        return 0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        try:
            return datetime.strptime(value[:25], "%a, %d %b %Y %H:%M:%S").replace(
                tzinfo=timezone.utc
            ).timestamp()
        except ValueError:
            return 0

def _reddit_post_from_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host not in {"reddit.com", "old.reddit.com"}:
        return None
    if "/comments/" not in parsed.path:
        return None
    post_id = parsed.path.split("/comments/", 1)[1].split("/", 1)[0]
    return f"reddit:{post_id}" if post_id else None

def _clean_text(value):
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)

def _is_relevant(title, body, query=""):
    text = f"{title} {body}".lower()

    # Reject service providers and unrelated marketing/social-media offers.
    if any(term in text for term in OFFER_TERMS):
        return False

    unrelated_only = (
        ("social media" in text or "social-media" in text)
        and not any(term in text for term in (
            "website", "web developer", "web designer", "wordpress",
            "shopify", "ecommerce", "online store", "landing page",
            "webflow", "frontend", "front-end",
        ))
    )
    if unrelated_only:
        return False

    # A valid prospect must contain BOTH a website-related signal and
    # a clear request/hiring signal. Incidental mentions of "website"
    # are not enough.
    website_signals = (
        "website", "web developer", "web designer", "wordpress",
        "shopify", "ecommerce", "online store", "landing page",
        "webflow", "frontend", "front-end", "website redesign",
        "redesign my site", "build a site", "create a site",
    )
    request_signals = (
        "need", "looking for", "looking to hire", "hiring", "hire",
        "seeking", "want to hire", "need help", "build", "create",
        "redesign", "developer", "designer", "agency",
    )

    has_website_signal = any(term in text for term in website_signals)
    has_request_signal = any(term in text for term in request_signals)

    if not (has_website_signal and has_request_signal):
        return False

    # Require a direct web-development/design intent phrase or a strong
    # combination of web + hiring/request language.
    direct_intent = any(term in text for term in INTENT_TERMS)
    strong_request = (
        has_website_signal
        and any(term in text for term in (
            "need a", "looking for", "looking to hire", "hiring",
            "seeking", "want a", "want to hire", "need help",
            "build me", "create me", "redesign",
        ))
    )

    if not (direct_intent or strong_request):
        return False

    # The supplied query must actually match when it is specific.
    query_words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
    if query_words:
        query_match = sum(word in text for word in query_words) >= min(2, len(query_words))
        if not query_match:
            return False

    return True

def _reddit_rss_candidates(session, subreddit, per_subreddit, seen, queries):
    # Reddit's JSON endpoint is returning 403 from GitHub Actions runners.
    # RSS is public and keeps the discovery source Reddit-only.
    endpoints = (
        f"https://old.reddit.com/r/{subreddit}/new/.rss",
        f"https://www.reddit.com/r/{subreddit}/new/.rss",
    )

    for url in endpoints:
        try:
            response = session.get(
                url,
                params={"limit": 100},
                headers={"Accept": "application/atom+xml,application/xml,text/xml"},
                timeout=20,
            )
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except (requests.RequestException, ET.ParseError) as exc:
            LOGGER.warning("Reddit RSS fetch failed: r/%s endpoint=%s error=%s",
                           subreddit, url, exc)
            continue

        found = []
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.findtext("{http://www.w3.org/2005/Atom}title") or ""
            content = entry.findtext("{http://www.w3.org/2005/Atom}content") or ""
            summary = entry.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            body = _clean_text(content or summary)
            published = entry.findtext("{http://www.w3.org/2005/Atom}published") or ""
            updated = entry.findtext("{http://www.w3.org/2005/Atom}updated") or ""
            created = _parse_reddit_date(published or updated)

            link = None
            for link_node in entry.findall("{http://www.w3.org/2005/Atom}link"):
                href = link_node.attrib.get("href")
                if href and "/comments/" in href:
                    link = href
                    break

            post_id = _reddit_post_from_url(link or "")
            if not post_id or not _post_age_ok(created):
                continue

            query = next((q for q in queries if _is_relevant(title, body, q)), "")
            if not query or post_id in seen:
                continue

            seen.add(post_id)
            found.append({
                "url": link,
                "domain": post_id,
                "title": title[:300],
                "description": body[:3000],
                "query": query,
                "source": "reddit",
                "subreddit": subreddit,
                "created_utc": created,
            })

            if len(found) >= per_subreddit:
                break

        if found:
            return found

        # A valid RSS response with zero matching posts is still useful;
        # don't hammer the second endpoint unnecessarily.
        return []

    return []

def _search_engine_candidates(session, query, per_query, seen):
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=_reddit_age_days())).date()
    search_query = (
        f'site:reddit.com/r/ ("{query}" OR "website" OR "web developer" OR "web designer") '
        f'after:{cutoff_date.isoformat()}'
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
            results = (
                soup.select("li.b_algo")
                or soup.select(".result")
                or soup.select("div[data-testid='result']")
            )
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

                snippet = (
                    result.select_one(".b_caption p")
                    or result.select_one(".result__snippet")
                    or result.select_one("p")
                )
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
    """Discover recent Reddit prospects without depending on Reddit JSON."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "YazoniiOS/1.5 prospect discovery by yazonii",
        "Accept-Language": "en-US,en;q=0.9",
    })

    found = []
    seen = set()
    per_subreddit = max(2, min(int(count), 20))

    for subreddit in SUBREDDITS:
        results = _reddit_rss_candidates(
            session, subreddit, per_subreddit, seen, queries
        )
        found.extend(results)
        LOGGER.info("Reddit RSS discovery: r/%s results=%s", subreddit, len(results))
        time.sleep(0.25)

    # If RSS cannot be reached, use search engines as a Reddit-only fallback.
    if not found:
        for query in queries:
            query = str(query).strip()
            if not query:
                continue
            results = _search_engine_candidates(session, query, count, seen)
            found.extend(results)
            LOGGER.info("Reddit search fallback: query=%r results=%s", query, len(results))
            if len(found) >= count:
                break
            time.sleep(0.25)

    LOGGER.info(
        "Reddit-only discovery complete: subreddits=%s queries=%s total=%s",
        len(SUBREDDITS), len(queries), len(found),
    )
    return found
