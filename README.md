# DropScout

DropScout is a consumer price-intelligence MVP: paste a public product URL, extract the current price, and build a simple price trail.

## Why this direction

Digital commerce keeps expanding, and subscription spending continues to grow. The product has a direct consumer value proposition: help people decide when a product is worth buying.

## MVP
- product URL input
- public-page fetching
- JSON-LD price extraction
- fallback price extraction
- current price display
- retailer link
- stored price history
- mobile-friendly UI

## Product roadmap
1. Watchlists
2. Scheduled rechecks
3. Price-drop notifications
4. Cross-retailer comparison
5. Product matching
6. Browser extension
7. Affiliate links
8. Personalized deal feeds

## Run
```bash
pip install -r requirements.txt
gunicorn app:app
```

No AI API is required.
