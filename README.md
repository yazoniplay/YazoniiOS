# Yazoni LeadFlow

LeadFlow is a small-business sales workspace built around one job: keep leads organized and turn follow-ups into revenue.

## Current product

- Account signup and password login
- Separate workspaces
- Workspace members and invite links
- Owner/member roles
- Lead pipeline with statuses
- Pipeline and won-value dashboard
- Follow-up dashboard
- CSV import/export
- Email actions
- Free / Pro / Team plan structure
- Stripe Checkout integration scaffold for recurring subscriptions
- Lead and seat limits by plan
- No AI dependency

## Run locally

```bash
pip install -r requirements.txt
set APP_PASSWORD=optional-legacy-password
set SECRET_KEY=replace-this
python app.py
```

Open `http://localhost:5000`.

## Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app
```

Recommended environment variables:

- `SECRET_KEY`
- `APP_PASSWORD` (optional legacy access)
- `STRIPE_SECRET_KEY`
- `STRIPE_PRO_PRICE_ID`
- `STRIPE_TEAM_PRICE_ID`

For real production data, use managed PostgreSQL rather than a local SQLite file. The current SQLite implementation is designed to keep the MVP easy to run while the product architecture is being validated.

## Billing

LeadFlow creates Stripe Checkout Sessions in subscription mode when Stripe is configured. Stripe Checkout handles payment collection; LeadFlow does not store card details.

A production launch should also add Stripe webhooks for subscription creation, renewal, cancellation, and failed payment state synchronization.

## Product roadmap

1. Accounts, workspaces and teams — implemented
2. Billing and subscription checkout — implemented as Stripe integration
3. Stripe webhooks and subscription state sync
4. Managed PostgreSQL
5. Role permissions and audit log
6. Automated follow-up email delivery
7. Analytics and revenue reporting
