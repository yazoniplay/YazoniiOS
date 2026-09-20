# YazoniiOS

Automated prospect intelligence: discover public business websites, crawl them, analyze observable opportunities with Gemini, score the evidence, store results, and deliver reports to Discord.

## Features

- Free public web-search discovery through DuckDuckGo HTML search
- Domain deduplication and SQLite persistence
- Public-site crawler with robots.txt support, same-domain limits, timeouts and byte/page caps
- Extraction of titles, descriptions, text and links
- Gemini structured analysis with evidence, pain points, opportunities, confidence and score
- Discord webhook reports
- Flask dashboard and JSON API
- Scheduled recurring scans

## Setup

Copy .env.example to .env and add your keys:

    GEMINI_API_KEY=
    DISCORD_WEBHOOK_URL=

No paid search API key is required.

Optional:

    GEMINI_MODEL=gemini-3.6-flash
    DATABASE_PATH=yazonii.db
    DISCOVERY_INTERVAL_MINUTES=60
    MAX_RESULTS_PER_QUERY=20
    MAX_CRAWL_PAGES=12
    MAX_CRAWL_CONCURRENCY=4
    CRAWL_TIMEOUT_SECONDS=12
    CRAWL_MAX_BYTES=1500000
    HONOR_ROBOTS=true
    DEFAULT_QUERIES=dentist stockholm,restaurant stockholm,construction company stockholm

## Run

    pip install -r requirements.txt
    python app.py

Open http://localhost:5000.

API:

    curl -X POST http://localhost:5000/api/scans -H "Content-Type: application/json" -d '{"queries":["dentist stockholm","restaurant stockholm"]}'

The crawler is limited to publicly reachable HTTP(S) pages and does not attempt authentication, CAPTCHA bypasses, stealth, or access-control circumvention. Search discovery uses the public DuckDuckGo HTML endpoint rather than a paid search API.
