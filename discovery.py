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
    """
    Accept only posts that look like a buyer/client asking for website work.

    The old filter was too semantic: a post could mention "website" somewhere
    and "hiring" somewhere else and still pass. This version uses explicit
    buyer-intent patterns and rejects provider/service posts before anything
    else.
    """
    title_text = (title or "").strip().lower()
    text = f"{title_text} {body or ''}".lower()
    compact = re.sub(r"\\s+", " ", text)

    # Provider/service-post signals. These are not prospects.
    provider_patterns = (
        r"\\[?for\\s*hire\\]?",
        r"\\bfor\\s+hire\\b",
        r"\\bavailable\\s+for\\s+hire\\b",
        r"\\bi(?:'m|\\s+am)\\s+(?:a\\s+)?(?:freelance|freelancer|web\\s+developer|web\\s+designer)\\b",
        r"\\b(?:web\\s+developer|web\\s+designer|freelance\\s+developer|freelancer)\\s+available\\b",
        r"\\bi\\s+(?:will|can|build|make|create|design)\\s+(?:you\\s+)?(?:a\\s+)?(?:website|web\\s+site)\\b",
        r"\\b(?:offering|offer)\\s+(?:web|website|web\\s+design|web\\s+development)\\b",
        r"\\bmy\\s+(?:web\\s+)?(?:development|design)\\s+services\\b",
        r"\\b(?:website|web)\\s+(?:development|design)\\s+services\\b",
        r"\\b(?:hire|contact|dm)\\s+me\\b.*\\b(?:website|web\\s+(?:developer|designer))\\b",
    )
    if any(re.search(pattern, compact, re.I | re.S) for pattern in provider_patterns):
        return False

    # Hard reject unrelated service categories unless the same post has a
    # concrete website build/redesign request.
    unrelated_terms = (
        "social media marketing", "social media management", "seo services",
        "search engine optimization", "google ads", "facebook ads",
        "paid ads", "content writer", "copywriter", "video editor",
        "graphic design services", "logo design services",
        "virtual assistant", "appointment setter", "lead generation service",
    )
    website_terms = (
        "website", "web site", "web developer", "web designer", "wordpress",
        "shopify", "woocommerce", "ecommerce", "e-commerce", "online store",
        "landing page", "webflow", "frontend", "front-end", "website redesign",
    )
    if any(term in compact for term in unrelated_terms):
        if not any(term in compact for term in website_terms):
            return False

    # A real buyer post needs an explicit buyer/request phrase AND a
    # website-specific object. Generic "hiring" + "website" is too loose.
    buyer_patterns = (
        r"\\bneed(?:s|ed)?\\b.{0,100}\\b(?:a\\s+)?(?:website|web\\s+site|web\\s+developer|web\\s+designer|wordpress|shopify|online\\s+store|landing\\s+page)\\b",
        r"\\b(?:website|web\\s+site|wordpress|shopify|online\\s+store|landing\\s+page)\\b.{0,100}\\b(?:need|needs|looking\\s+for|looking\\s+to\\s+hire|hiring|hire|seeking|want|want\\s+to\\s+hire)\\b",
        r"\\b(?:looking\\s+for|looking\\s+to\\s+hire|seeking|want(?:s)?\\s+to\\s+hire|hiring)\\b.{0,100}\\b(?:web\\s+developer|web\\s+designer|website|web\\s+site|wordpress|shopify|ecommerce|e-commerce|online\\s+store|landing\\s+page)\\b",
        r"\\b(?:build|create|make|redesign|revamp|rebuild)\\b.{0,100}\\b(?:my|our|a|the)\\s+(?:website|web\\s+site|site|shopify\\s+store|online\\s+store)\\b",
        r"\\b(?:my|our)\\s+(?:website|web\\s+site|site)\\b.{0,100}\\b(?:outdated|old|broken|terrible|needs?\\s+(?:a\\s+)?(?:redesign|revamp|rebuild|work))\\b",
        r"\\b(?:need|looking\\s+for|seeking)\\b.{0,100}\\b(?:someone|person|developer|designer|agency)\\b.{0,100}\\b(?:website|web\\s+site|shopify|wordpress|ecommerce)\\b",
    )
    if not any(re.search(pattern, compact, re.I | re.S) for pattern in buyer_patterns):
        return False

    # Reject posts whose only "website" mention is an example, portfolio,
    # link, or discussion topic rather than the thing they want built.
    if not any(re.search(pattern, compact, re.I | re.S) for pattern in buyer_patterns):
        return False

    # If a specific discovery query is supplied, require its meaningful
    # terms to occur in the post. Ignore filler words like "a", "my", "for".
    query_words = [
        w for w in re.findall(r"[a-z0-9]+", str(query).lower())
        if len(w) > 3 and w not in {"need", "looking", "website", "with", "help"}
    ]
    if query_words and not any(word in compact for word in query_words):
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
