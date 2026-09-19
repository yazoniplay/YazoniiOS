# FORGE

FORGE is a creator-commerce marketplace MVP.

The product thesis: creators should be able to publish useful digital products and give their audience one focused place to discover and buy them. The marketplace can later add creator payouts, real checkout, affiliate links, subscriptions, analytics, licensing and audience-owned storefronts.

## What is built now

- Public marketplace/discovery page
- Search
- Category filtering
- Creator accounts
- Creator handles
- Creator storefront dashboard
- Product publishing
- Product detail pages
- Demo checkout flow
- SQLite persistence
- Responsive dark/orange interface
- Password hashing
- No AI dependency

## Why this direction

Creator businesses are increasingly diversifying beyond ads into memberships, products and commerce. Current 2026 creator research also points to creators professionalizing their businesses and treating ownership/licensing and monetization infrastructure as important problems.

The MVP intentionally proves the core loop before adding payment complexity:

creator -> product -> discovery -> product page -> purchase intent

## Run

```bash
pip install -r requirements.txt
set SECRET_KEY=replace-with-a-long-random-secret
python app.py
```

Open http://localhost:5000

## Render

Build:

```bash
pip install -r requirements.txt
```

Start:

```bash
gunicorn app:app
```

Environment variable:

- SECRET_KEY

## Next build

1. Real checkout
2. Creator payout/onboarding flow
3. Digital file delivery
4. Creator storefront URLs
5. Reviews and ratings
6. Creator analytics
7. Affiliate/commission links
8. Moderation and reporting
9. PostgreSQL for production
