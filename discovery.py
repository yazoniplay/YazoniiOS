import os
import time
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class DiscoveryError(Exception):
    pass


SEARCH_URL = "https://html.duckduckgo.com/html/"


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


def discover(queries, count=20):
    """Discover public business websites without a paid search API."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; YazoniiOS/1.0; "
                "+https://github.com/yazoniplay/YazoniiOS)"
            ),
            "Accept-Language": "en-US,en;q=0.8",
        }
    )

    found = []
    seen = set()
    per_query = max(1, min(int(count), 50))

    for index, query in enumerate(queries):
        query = str(query).strip()
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
            raise DiscoveryError(
                f"Search failed for '{query}': {exc}"
            ) from exc

        soup = BeautifulSoup(response.text, "html.parser")
        results = soup.select(".result")

        if not results:
            results = soup.select("div[data-testid='result']")

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
                }
            )
            added += 1

        if index < len(queries) - 1:
            time.sleep(1)

    return found
