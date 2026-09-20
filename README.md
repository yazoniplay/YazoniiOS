# YazoniiOS

YazoniiOS is an automated prospect-intelligence system for discovering public business websites, crawling their public pages, analyzing opportunities with Gemini, scoring prospects, and delivering actionable reports to Discord.

## What it does

- Discover businesses from configurable search queries using the Brave Search API.
- Deduplicate domains and persist prospects in SQLite.
- Crawl the public website with robots.txt awareness, same-domain limits, timeouts, size limits, and URL normalization.
- Extract useful business/site signals: title, description, headings, contact signals, social links, forms, analytics, CMS hints, HTTPS, performance-related hints, missing metadata, and page inventory.
- Analyze the evidence with Gemini and require structured JSON output.
- Score opportunities using transparent deterministic factors plus the AI analysis.
- Send rich prospect reports to Discord through a webhook.
- Run on demand or continuously on a configurable schedule.
- Keep API keys and webhooks in environment variables.

## Environment

Copy `.env.example` to `.env` and configure:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (default: `gemini-3.6-flash`)
- `BRAVE_SEARCH_API_KEY`
- `DISCORD_WEBHOOK_URL`
- `DATABASE_PATH` (default: `yazonii.db`)
- `DISCOVERY_INTERVAL_MINUTES` (default: `60`)
- `MAX_RESULTS_PER_QUERY` (default: `20`)
- `MAX_CRAWL_PAGES` (default: `12`)
- `CRAWL_CONCURRENCY` (default: `4`)

## Run

```bash
pip install -r requirements.txt
python app.py
```

Dashboard: `http://localhost:5000`

Run a scan from the dashboard or:

```bash
curl -X POST http://localhost:5000/api/scans \
  -H "Content-Type: application/json" \
  -d '{"queries":["dentist stockholm","restaurant stockholm","construction company stockholm"]}'
```

The service also exposes `/health`.

## Safety and crawling boundaries

The crawler only requests publicly reachable HTTP(S) pages, honors robots.txt when enabled, stays on the target domain, limits page count/size, and does not attempt authentication, CAPTCHA bypasses, stealth, or access-control circumvention.

## Architecture

```
Discovery -> Domain normalization -> Crawl -> Signal extraction -> Gemini analysis -> Scoring -> SQLite -> Discord
```
