# Yazoni LeadFlow

A focused sales pipeline MVP for small businesses.

## What it solves
LeadFlow keeps potential customers, pipeline value, statuses, notes, and next follow-up dates in one place.

## Run locally
```bash
pip install -r requirements.txt
set APP_PASSWORD=your-password
python app.py
```

On Render:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variables: `APP_PASSWORD`, `SECRET_KEY`
- For production persistence, attach a persistent disk or move the database to managed PostgreSQL.

## MVP roadmap
1. Lead dashboard and pipeline
2. Follow-up reminders
3. Import leads from CSV
4. Email integrations
5. Team accounts
6. Stripe subscriptions

This repository intentionally has no AI dependency.