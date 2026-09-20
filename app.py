import os
import threading
from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv

from db import init_db, list_prospects, get_stats, save_scan
from pipeline import run_scan
from scheduler import start_scheduler

load_dotenv()
init_db()

app = Flask(__name__)
_scan_lock = threading.Lock()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YazoniiOS · Prospect Intelligence</title>
<style>
:root{--bg:#07090d;--panel:#0f131a;--line:#202733;--text:#f5f7fb;--muted:#8e98a8;--accent:#ff6900;--green:#65d39b;--red:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#1b120c 0,#07090d 34%),var(--bg);color:var(--text);font:14px Inter,system-ui,sans-serif}
.wrap{max-width:1220px;margin:auto;padding:0 22px}nav{height:70px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}.brand{font-weight:950;letter-spacing:-.5px}.brand span{color:var(--accent)}.muted{color:var(--muted)}
.hero{padding:54px 0 28px}.eyebrow{color:#ff9b5b;text-transform:uppercase;font-size:11px;font-weight:900;letter-spacing:1.7px}h1{font-size:clamp(36px,6vw,64px);line-height:.98;letter-spacing:-3px;margin:10px 0}.lead{max-width:720px;color:var(--muted);font-size:17px;line-height:1.55}
.controls{display:flex;gap:8px;margin:24px 0}.controls input{flex:1;min-width:0;background:#0b0e13;border:1px solid var(--line);color:#fff;border-radius:10px;padding:12px}.btn{border:1px solid var(--line);background:#151a22;color:#fff;border-radius:10px;padding:11px 15px;font-weight:850;cursor:pointer}.primary{background:var(--accent);border-color:var(--accent);color:#111}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat,.card{background:rgba(15,19,26,.92);border:1px solid var(--line);border-radius:14px}.stat{padding:17px}.stat b{display:block;font-size:27px;margin-top:5px}
.table{margin-top:14px;overflow:auto}.row{display:grid;grid-template-columns:1.3fr .7fr .6fr .8fr 100px;gap:12px;align-items:center;padding:15px 17px;border-top:1px solid var(--line);min-width:800px}.row.head{border-top:0;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:1px}.score{font-weight:950}.high{color:var(--green)}.mid{color:#ffd166}.low{color:var(--muted)}a{color:inherit;text-decoration:none}.url{color:#ff9b5b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.badge{display:inline-block;padding:5px 8px;border-radius:999px;background:#1b2029;font-size:11px;font-weight:800}.footer{padding:35px 0;color:var(--muted);font-size:12px}
@media(max-width:800px){.stats{grid-template-columns:1fr 1fr}.controls{flex-direction:column}}
</style>
</head>
<body><div class="wrap">
<nav><div class="brand">YAZONIIOS<span>.</span></div><div class="muted">Prospect Intelligence</div></nav>
<section class="hero"><div class="eyebrow">Automated discovery · crawl · AI analysis · Discord</div>
<h1>Find the businesses worth knowing.</h1>
<p class="lead">YazoniiOS discovers public business websites, audits their online presence, identifies concrete opportunities, scores the evidence, and sends the report to Discord.</p>
<form class="controls" method="post" action="/scan"><input name="queries" placeholder="dentist stockholm, restaurant stockholm,..." value="{{ default_queries }}"><button class="btn primary">Run scan</button></form></section>
<section class="stats">
<div class="stat"><span class="muted">Prospects</span><b>{{ stats.prospects }}</b></div>
<div class="stat"><span class="muted">Analyzed</span><b>{{ stats.analyzed }}</b></div>
<div class="stat"><span class="muted">Reports sent</span><b>{{ stats.sent }}</b></div>
<div class="stat"><span class="muted">High-opportunity</span><b>{{ stats.high }}</b></div>
</section>
<section class="card table"><div class="row head"><div>Business</div><div>Opportunity</div><div>Confidence</div><div>Status</div><div>Open</div></div>
{% for p in prospects %}<div class="row"><div><b>{{ p.name or p.domain }}</b><div class="url">{{ p.domain }}</div></div><div class="score {% if p.opportunity_score >= 75 %}high{% elif p.opportunity_score >= 50 %}mid{% else %}low{% endif %}">{{ p.opportunity_score }}/100</div><div>{{ p.confidence or 0 }}/100</div><div><span class="badge">{{ p.status }}</span></div><div><a class="btn" href="{{ p.url }}" target="_blank">Site ↗</a></div></div>{% endfor %}
</section>
<footer class="footer">Public-web intelligence only. No authentication or access-control bypassing.</footer>
</div></body></html>"""


@app.get("/")
def home():
    return render_template_string(
        PAGE,
        stats=get_stats(),
        prospects=list_prospects(100),
        default_queries=os.getenv("DEFAULT_QUERIES", ""),
    )


@app.post("/scan")
def scan_form():
    queries = [x.strip() for x in request.form.get("queries", "").split(",") if x.strip()]
    if not queries:
        return jsonify({"error": "Add at least one search query."}), 400
    if not _scan_lock.acquire(blocking=False):
        return jsonify({"error": "A scan is already running."}), 409
    try:
        result = run_scan(queries)
        save_scan(queries, result)
        return jsonify(result)
    finally:
        _scan_lock.release()


@app.post("/api/scans")
def scan_api():
    payload = request.get_json(silent=True) or {}
    queries = payload.get("queries") or []
    if isinstance(queries, str):
        queries = [queries]
    queries = [str(x).strip() for x in queries if str(x).strip()]
    if not queries:
        return jsonify({"error": "queries must contain at least one search query"}), 400
    if not _scan_lock.acquire(blocking=False):
        return jsonify({"error": "A scan is already running."}), 409
    try:
        result = run_scan(queries)
        save_scan(queries, result)
        return jsonify(result)
    finally:
        _scan_lock.release()


@app.get("/api/prospects")
def prospects_api():
    return jsonify([dict(x) for x in list_prospects(250)])


@app.get("/api/stats")
def stats_api():
    return jsonify(get_stats())


@app.get("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    start_scheduler()
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=False,
    )
