import os
import requests


def clip(value, limit=1024):
    return str(value or "").strip()[:limit]


def send_report(prospect):
    webhook = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook:
        return False

    score = int(prospect.get("opportunity_score", 0))
    confidence = int(prospect.get("confidence", 0))
    color = 0x65D39B if score >= 75 else 0xFFB84D if score >= 50 else 0x6F7785
    fields = [
        {"name": "Opportunity", "value": f"**{score}/100**", "inline": True},
        {"name": "Confidence", "value": f"**{confidence}/100**", "inline": True},
        {"name": "Category", "value": clip(prospect.get("category", "unknown"), 100), "inline": True},
        {"name": "Summary", "value": clip(prospect.get("summary", "No summary"))},
    ]
    if prospect.get("pain_points"):
        fields.append({"name": "Signals", "value": clip("\n".join("• " + item for item in prospect["pain_points"]))})
    if prospect.get("opportunities"):
        fields.append({"name": "Opportunities", "value": clip("\n".join("• " + item for item in prospect["opportunities"]))})
    fields.append({"name": "Recommended action", "value": clip(prospect.get("recommended_action", ""))})
    if prospect.get("pitch_subject"):
        fields.append({"name": "AI pitch subject", "value": clip(prospect["pitch_subject"], 250)})
    if prospect.get("pitch"):
        fields.append({"name": "AI pitch — adapt manually", "value": clip(prospect["pitch"])})
    if prospect.get("pitch_notes"):
        fields.append({"name": "Pitch notes", "value": clip("\n".join("• " + item for item in prospect["pitch_notes"]))})

    payload = {
        "username": "YazoniiOS",
        "allowed_mentions": {"parse": []},
        "embeds": [{
            "title": clip(prospect.get("name") or prospect.get("domain") or "Prospect", 256),
            "url": prospect.get("url"),
            "description": "Automated public-web prospect intelligence. Outreach is manual and should be personalized before sending.",
            "color": color,
            "fields": fields,
            "footer": {"text": "YazoniiOS · public-web intelligence"},
        }],
    }
    response = requests.post(webhook, json=payload, timeout=15)
    response.raise_for_status()
    return True
