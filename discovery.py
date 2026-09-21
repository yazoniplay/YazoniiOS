import os
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class DiscoveryError(Exception):
    pass


SEARCH_URL = "https://html.duckduckgo.com/html/"
REDDIT_SEARCH_URL = "https://www.reddit.com/search.json"


def _clean_result_url(href):
    if not href:
        return None
    href = urljoin(SEARCH_URL, href)
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
    host = urlparse(url).hostname or ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def _reddit_age_days():
    return max(1, min(int(os.getenv("REDDIT_MAX_AGE_DAYS", "5")), 7))


def _reddit_candidates_from_search(session, query, per_query, seen):
    """Fallback for environments where Reddit blocks direct API requests."""
    max_age_days = _reddit_age_days()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).date()
    search_query = f"site:reddit.com {query} after:{cutoff_date.isoformat()}"

    response = session.get(
        SEARCH_URL,
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

        url = _clean_result_url(anchor.get("href"))
        if not url:
            continue

        host = _host(url)
        if host not in {"reddit.com", "old.reddit.com", "www.reddit.com"}:
            continue

        parsed = urlparse(url)
        if not parsed.path.startswith(("/r/", "/comments/")):
            continue

        post_match = parsed.path.split("/comments/")
        post_id = post_match[1].split("/")[0] if len(post_match) == 2 else parsed.path

        domain = f"reddit:{post_id}"
        if domain in seen:
            continue

        description_node = result.select_one(".result__snippet") or result.select_one(
            "[data-result='snippet']"
        )
        description = (
            description_node.get_text(" ", strip=True)
            if description_node
            else ""
        )

        seen.add(domain)
        found.append(
            {
                "url": url,
                "domain": domain,
                "title": anchor.get_text(" ", strip=True) or "Reddit discussion",
                "description": description[:3000],
                "query": query,
                "source": "reddit",
                "subreddit": "",
            }
        )

    return found


def _reddit_candidates(session, query, per_query, seen):
    max_age_days = _reddit_age_days()
    cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)

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
            headers={"Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        # GitHub Actions and other cloud IP ranges can be blocked by Reddit.
        # Fall back to public search-engine results instead of killing the scan.
        try:
            return _reddit_candidates_from_search(session, query, per_query, seen)
        except (requests.RequestException, ValueError) as exc:
            # Reddit is an enrichment source, so a failure here should not
            # prevent the main web discovery pipeline from running.
            return []

    found = []

    for child in payload.get("data", {}).get("children", []):
        data = child.get("data") or {}
        created = float(data.get("created_utc") or 0)
        permalink = data.get("permalink")
        post_id = data.get("id")

        if not permalink or not post_id or created < cutoff:
            continue

        url = "https://www.reddit.com" + permalink
        domain = f"reddit:{post_id}"
        if domain in seen:
            continue

        seen.add(domain)
        found.append(
            {
                "url": url,
                "domain": domain,
                "title": data.get("title") or "Reddit discussion",
                "description": BeautifulSoup(
                    data.get("selftext") or "", "html.parser"
                ).get_text(" ", strip=True)[:3000],
                "query": query,
                "source": "reddit",
                "subreddit": data.get("subreddit", ""),
                "created_utc": created,
            }
        )

    return found


def discover(queries, count=20):
    """Discover public websites and recent Reddit discussions without a paid API."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "YazoniiOS/1.0 public prospect discovery",
            "Accept-Language": "en-US,en;q=0.8",
        }
    )

    found = []
    seen = set()
    per_query = max(1, min(int(count), 50))

    for index, raw_query in enumerate(queries):
        query = str(raw_query).strip()
        if not query:
            continue

        try:
            response = session.get(
                SEARCH_URL,
                params={"q": query, "kl": "wt-wt"},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DiscoveryError(f"Search failed for '{query}': {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select(".result") or soup.select("div[data-testid='result']")
        added = 0

        for result in results:
            if added >= per_query:
                break

            anchor = result.select_one("a.result__a") or result.select_one(
                "a[data-testid='result-title-a']"
            )
            if not anchor:
                continue

            url = _clean_result_url(anchor.get("href"))
            if not url:
                continue

            domain = _host(url)
            if not domain or domain in seen:
                continue

            title = anchor.get_text(" ", strip=True)
            description_node = result.select_one(".result__snippet") or result.select_one(
                "[data-result='snippet']"
            )
            description = (
                description_node.get_text(" ", strip=True)
                if description_node
                else ""
            )

            seen.add(domain)
            found.append(
                {
                    "url": url,
                    "domain": domain,
                    "title": title,
                    "description": description,
                    "query": query,
                    "source": "web",
                }
            )
            added += 1

        found.extend(_reddit_candidates(session, query, per_query, seen))

        if index < len(queries) - 1:
            time.sleep(1)

    return found
