# AccessPulse

AccessPulse is an EU-first website accessibility monitoring MVP.

## Why this market

The European Accessibility Act entered application on June 28, 2025. The European Commission says covered services include e-commerce, and the EU estimates around 100 million people in the EU live with a disability. Accessibility is therefore not just a design preference; for covered businesses it can become a compliance and market-access concern.

## MVP

Paste a public URL and AccessPulse performs a fast automated pre-check for common issues:

- missing image alt attributes
- missing HTML language
- missing page title
- missing headings
- missing main landmark
- missing viewport metadata
- missing form labels
- apparently empty controls
- obsolete motion elements

It produces a score and a concrete fix list.

## Important

This is **not legal certification** and automated tests cannot establish full WCAG/EN 301 549 conformance. It is a lead-generation and monitoring starting point.

## Next build

1. Crawl an entire domain
2. WCAG/EN 301 549 rule engine
3. Scheduled rescans
4. Change detection
5. PDF/CSV reports
6. Accessibility statement generator
7. Shopify/WooCommerce connectors
8. Team workspaces
9. Paid monitoring plans
10. Human-audit marketplace/integration

## Run

```bash
pip install -r requirements.txt
python app.py
```

Render start:

```bash
gunicorn app:app
```
