# AGENTREADY

AGENTREADY is an MVP for the emerging agentic-commerce layer.

## What it does

Merchants enter product information once. AGENTREADY normalizes it into clean, machine-readable product records containing:

- product name and description
- price and currency
- availability
- shipping information
- product URL
- structured attributes

The product record can then become the base for future integrations with AI shopping channels and agent-commerce protocols.

## Why this direction

AI shopping is moving from simple recommendations toward discovery, checkout and autonomous purchasing. OpenAI/Stripe's Agentic Commerce Protocol and Shopify/Google's Universal Commerce Protocol are examples of the infrastructure shift. Shopify reports AI-driven traffic and AI-originated orders growing rapidly in 2026.

The opportunity is not to compete with the major AI platforms. It is to build the merchant-side compatibility layer that lets smaller merchants participate across emerging agent channels.

## MVP

- Merchant accounts
- Product catalog
- Structured machine-readable output
- Availability/shipping fields
- Product URLs
- Dashboard
- Responsive UI
- SQLite persistence
- No AI API dependency

## Next build

1. Import Shopify/WooCommerce catalogs
2. Automatic catalog validation
3. JSON-LD generation
4. ACP/UCP-compatible endpoints
5. AI-channel visibility monitoring
6. AI-originated order attribution
7. Usage/transaction pricing

## Run

```bash
pip install -r requirements.txt
python app.py
```

Render start command:

```bash
gunicorn app:app
```
