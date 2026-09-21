import logging
import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class DiscoveryError(Exception):
    pass


DDG_HTML_URL = "https://html.duckduckgo.com/html/"
DDG_LITE_URL = "https://lite.duckduckgo.com/lite/"
BING_RSS_URL = "https://www.bing.com/search"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"
LOGGER = logging.getLogger(__name__)

# Never treat listing/directory/social platforms as the prospect itself.
EXCLUDED_PROSPECT_HOSTS = {
    "yelp.com","yellowpages.com","foursquare.com","tripadvisor.com","mapquest.com",
    "manta.com","superpages.com","bbb.org","chamberofcommerce.com","alignable.com",
    "hotfrog.com","merchantcircle.com","brownbook.net","cylex.us.com","citysearch.com",
    "local.com","porch.com","angi.com","homeadvisor.com","thumbtack.com",
    "facebook.com","instagram.com","linkedin.com","x.com","twitter.com","tiktok.com",
    "youtube.com","crunchbase.com","clutch.co","upcity.com","expertise.com",
    "yellowbook.com","411.com","bizapedia.com","dnb.com","indeed.com","glassdoor.com",
    "ziprecruiter.com","wikipedia.org","reddit.com","old.reddit.com",
}

EXCLUDED_PATH_MARKERS = (
    "/directory/","/directories/","/business-directory/","/businesses/",
    "/listing/","/listings/","/company-directory/","/local-directory/",
)


def _clean_result_url(href, base_url=DDG_HTML_URL):
    if not href:
        return None
    href = urljoin(base_url, href)
    parsed = urlparse(href)
    if parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [None])[0]
        if target:
            href = unquote(target)
    parsed = urlparse(href)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return href


def _host(url):
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _reddit_age_days():
    try:
        value = int(os.getenv("REDDIT_MAX_AGE_DAYS", "5"))
    except ValueError:
        value = 5
    return max(1, min(value, 5))


def _parse_search_results(html, base_url, query, source="web", per_query=20):
    soup = BeautifulSoup(html, "html.parser")
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
        url = _clean_result_url(anchor.get("href"), base_url)
        if not url:
            continue
        host = _host(url)
        path = urlparse(url).path.lower()
        if host in EXCLUDED_PROSPECT_HOSTS:
            continue
        if any(marker in path for marker in EXCLUDED_PATH_MARKERS):
            continue
        description_node = result.select_one(".result__snippet") or result.select_one(
            "[data-result='snippet']"
        )
        found.append(
            {
                "url": url,
                "domain": _host(url),
                "title": anchor.get_text(" ", strip=True),
                "description": description_node.get_text(" ", strip=True) if description_node else "",
                "query": query,
                "source": source,
            }
        )
    return found


def _bing_rss_candidates(session, query, per_query):
    response = session.get(
        BING_RSS_URL,
        params={"q": query, "format": "rss"},
        headers={"Accept": "application/rss+xml, application/xml, text/xml"},
        timeout=15,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "xml")
    found = []
    for item in soup.select("item")[:per_query]:
        link = item.find("link")
        title = item.find("title")
        description = item.find("description")
        url = _clean_result_url(link.get_text(strip=True) if link else "", BING_RSS_URL)
        if not url:
            continue
        host = _host(url)
        path = urlparse(url).path.lower()
        if host in EXCLUDED_PROSPECT_HOSTS:
            continue
        if any(marker in path for marker in EXCLUDED_PATH_MARKERS):
            continue
        found.append(
            {
                "url": url,
                "domain": _host(url),
                "title": title.get_text(" ", strip=True) if title else "Web result",
                "description": description.get_text(" ", strip=True) if description else "",
                "query": query,
                "source": "web",
            }
        )
    return found


def _web_candidates(session, query, per_query):
    errors = []
    for endpoint, base in ((DDG_HTML_URL, DDG_HTML_URL), (DDG_LITE_URL, DDG_LITE_URL)):
        try:
            response = session.get(
                endpoint,
                params={"q": query, "kl": "wt-wt"},
                timeout=15,
            )
            response.raise_for_status()
            results = _parse_search_results(response.text, base, query, "web", per_query)
            if results:
                return results
            errors.append(f"{endpoint}: no parsable results")
        except requests.RequestException as exc:
            errors.append(f"{endpoint}: {exc}")

    try:
        results = _bing_rss_candidates(session, query, per_query)
        if results:
            return results
        errors.append("Bing RSS: no results")
    except requests.RequestException as exc:
        errors.append(f"Bing RSS: {exc}")

    LOGGER.warning("No web results for %r. Providers: %s", query, " | ".join(errors))
    return []


def _reddit_candidates_from_search(session, query, per_query, seen):
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=_reddit_age_days())).date()
    search_query = f"site:reddit.com {query} after:{cutoff_date.isoformat()}"
    results = _web_candidates(session, search_query, per_query)
    found = []

    for result in results:
        url = result["url"]
        parsed = urlparse(url)
        host = _host(url)
        if host not in {"reddit.com", "old.reddit.com"}:
            continue
        if not parsed.path.startswith(("/r/", "/comments/")):
            continue
        post_match = parsed.path.split("/comments/")
        post_id = post_match[1].split("/")[0] if len(post_match) == 2 else parsed.path
        domain = f"reddit:{post_id}"
        if domain in seen:
            continue
        seen.add(domain)
        result.update({"domain": domain, "source": "reddit", "subreddit": ""})
        found.append(result)
    return found


def _reddit_candidates(session, query, per_query, seen):
    cutoff = datetime.now(timezone.utc).timestamp() - (_reddit_age_days() * 86400)
    try:
        response = session.get(
            REDDIT_SEARCH_URL,
            params={"q": query, "sort": "new", "t": "week", "limit": per_query, "raw_json": 1},
            headers={"Accept": "application/json", "User-Agent": "YazoniiOS/1.1 public discovery"},
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
        found.append(
            {
                "url": "https://www.reddit.com" + permalink,
                "domain": domain,
                "title": data.get("title") or "Reddit discussion",
                "description": BeautifulSoup(data.get("selftext") or "", "html.parser").get_text(" ", strip=True)[:3000],
                "query": query,
                "source": "reddit",
                "subreddit": data.get("subreddit", ""),
                "created_utc": created,
            }
        )
    return found


def discover(queries, count=20):
    """Discover public web prospects and Reddit discussions from the last 1-5 days."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "YazoniiOS/1.1 public prospect discovery",
            "Accept-Language": "en-US,en;q=0.8",
        }
    )

    found = []
    seen = set()
    per_query = max(1, min(int(count), 50))
    stats = {"web": 0, "reddit": 0, "queries": 0}

    for index, raw_query in enumerate(queries):
        query = str(raw_query).strip()
        if not query:
            continue
        stats["queries"] += 1

        for result in _web_candidates(session, query, per_query):
            domain = result.get("domain")
            if not domain or domain in seen:
                continue
            seen.add(domain)
            found.append(result)
            stats["web"] += 1

        for result in _reddit_candidates(session, query, per_query, seen):
            found.append(result)
            stats["reddit"] += 1

        if index < len(queries) - 1:
            time.sleep(1)

    LOGGER.info("Discovery summary: queries=%s web=%s reddit=%s total=%s", stats["queries"], stats["web"], stats["reddit"], len(found))
    return found
