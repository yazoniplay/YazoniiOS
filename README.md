# SIGNAL

SIGNAL is a demand-discovery network MVP.

The thesis is deliberately different from the previous products: instead of building another marketplace or SaaS dashboard and hoping people want it, SIGNAL collects concrete problems from users and makes demand visible.

## MVP

- Public demand feed
- Search and topic filters
- User accounts
- Public problem/demand signals
- Urgency scoring
- Related signals
- Personal signal dashboard
- Responsive dark interface
- SQLite persistence
- No AI dependency

## Core loop

person has a problem -> posts it -> others discover the same need -> builders can see concentrated demand -> future versions can let users follow/pledge interest and connect builders with demand.

## Why this direction

Current 2026 app research points to users caring more about solving real problems and fixing broken basics than adding novelty. Recent complaint analysis also shows growth/customer acquisition and concrete unmet needs remain recurring pain points. The product is designed around revealed demand rather than a generic feature list.

## Run

```bash
pip install -r requirements.txt
set SECRET_KEY=replace-with-a-long-random-secret
python app.py
```

Open http://localhost:5000

## Render

Build: `pip install -r requirements.txt`

Start: `gunicorn app:app`

Environment variable: `SECRET_KEY`

## Next if validated

1. Follow a signal
2. Vote/pledge interest
3. Builder profiles
4. Demand clustering
5. Verified proof-of-need
6. Paid research / buyer-intent signals
7. Builder-to-user matching
8. PostgreSQL and moderation
