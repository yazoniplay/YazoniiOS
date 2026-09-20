import os
import threading
from flask import Flask, jsonify, render_template_string, request
from dotenv import load_dotenv
from db import init_db, list_prospects, get_stats, save_scan
from pipeline import run_scan
from scheduler import start_scheduler

load_dotenv()
init_db()
app=Flask(__name__)
lock=threading.Lock()

PAGE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>YazoniiOS</title>
<style>
:root{--bg:#07090d;--p:#10141b;--l:#202733;--t:#f5f7fb;--m:#8d97a7;--a:#ff6900;--g:#65d39b}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% 0,#21140b 0,#07090d 34%),var(--bg);color:var(--t);font:14px system-ui,sans-serif}.wrap{max-width:1200px;margin:auto;padding:0 22px}nav{height:70px;border-bottom:1px solid var(--l);display:flex;align-items:center;justify-content:space-between}.brand{font-weight:950}.brand span{color:var(--a)}.muted{color:var(--m)}.hero{padding:55px 0 28px}.ey{color:#ff9b5b;text-transform:uppercase;font-size:11px;font-weight:900;letter-spacing:1.6px}h1{font-size:clamp(38px,6vw,64px);line-height:.98;letter-spacing:-3px;margin:10px 0 16px}.lead{max-width:720px;color:var(--m);font-size:17px;line-height:1.55}.form{display:flex;gap:8px;margin:24px 0}.form input{flex:1;background:#0b0e13;border:1px solid var(--l);color:#fff;border-radius:10px;padding:12px}.btn{border:1px solid var(--l);background:#151a22;color:#fff;border-radius:10px;padding:11px 15px;font-weight:850}.primary{background:var(--a);border-color:var(--a);color:#111}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.stat,.table{background:rgba(16,20,27,.94);border:1px solid var(--l);border-radius:14px}.stat{padding:17px}.stat b{display:block;font-size:27px;margin-top:5px}.table{margin-top:14px;overflow:auto}.row{display:grid;grid-template-columns:1.4fr .7fr .7fr .8fr 80px;gap:12px;align-items:center;padding:15px 17px;border-top:1px solid var(--l);min-width:800px}.head{border-top:0;color:var(--m);font-size:11px;text-transform:uppercase;letter-spacing:1px}.score{font-weight:950}.high{color:var(--g)}.mid{color:#ffd166}.low{color:var(--m)}.url{color:#ff9b5b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.badge{padding:5px 8px;border-radius:999px;background:#1b2029;font-size:11px;font-weight:800}a{color:inherit;text-decoration:none}.footer{padding:35px 0;color:var(--m);font-size:12px}@media(max-width:800px){.stats{grid-template-columns:1fr 1fr}.form{flex-direction:column}}
</style></head><body><div class="wrap"><nav><div class="brand">YAZONIIOS<span>.</span></div><div class="muted">Prospect Intelligence</div></nav>
<section class="hero"><div class="ey">Discovery · Crawl · Gemini · Discord</div><h1>Find the businesses worth knowing.</h1><p class="lead">Discover public business websites, audit their online presence, identify evidence-backed opportunities, and deliver the result to Discord.</p>
<form class="form" method="post" action="/scan"><input name="queries" placeholder="dentist stockholm, restaurant stockholm..." value="{{default_queries}}"><button class="btn primary">Run scan</button></form></section>
<section class="stats"><div class="stat"><span class="muted">Prospects</span><b>{{stats.prospects}}</b></div><div class="stat"><span class="muted">Analyzed</span><b>{{stats.analyzed}}</b></div><div class="stat"><span class="muted">Reports sent</span><b>{{stats.sent}}</b></div><div class="stat"><span class="muted">High opportunity</span><b>{{stats.high}}</b></div></section>
<section class="table"><div class="row head"><div>Business</div><div>Opportunity</div><div>Confidence</div><div>Status</div><div>Site</div></div>
{%for p in prospects%}<div class="row"><div><b>{{p.name or p.domain}}</b><div class="url">{{p.domain}}</div></div><div class="score {%if p.opportunity_score>=75%}high{%elif p.opportunity_score>=50%}mid{%else%}low{%endif%}">{{p.opportunity_score}}/100</div><div>{{p.confidence}}/100</div><div><span class="badge">{{p.status}}</span></div><div><a class="btn" href="{{p.url}}" target="_blank">↗</a></div></div>{%endfor%}</section>
<footer class="footer">Public-web intelligence only. No authentication or access-control bypassing.</footer></div></body></html>"""

@app.get("/")
def home():
    return render_template_string(PAGE,stats=get_stats(),prospects=list_prospects(100),default_queries=os.getenv("DEFAULT_QUERIES",""))

@app.post("/scan")
def scan_form():
    queries=[x.strip() for x in request.form.get("queries","").split(",") if x.strip()]
    if not queries:return jsonify({"error":"Add at least one search query."}),400
    if not lock.acquire(False):return jsonify({"error":"A scan is already running."}),409
    try:
        result=run_scan(queries);save_scan(queries,result);return jsonify(result)
    finally:lock.release()

@app.post("/api/scans")
def scan_api():
    payload=request.get_json(silent=True) or {}; queries=payload.get("queries") or []
    if isinstance(queries,str):queries=[queries]
    queries=[str(x).strip() for x in queries if str(x).strip()]
    if not queries:return jsonify({"error":"queries must contain at least one search query"}),400
    if not lock.acquire(False):return jsonify({"error":"A scan is already running."}),409
    try:
        result=run_scan(queries);save_scan(queries,result);return jsonify(result)
    finally:lock.release()

@app.get("/api/prospects")
def prospects():return jsonify([dict(x) for x in list_prospects(250)])

@app.get("/api/stats")
def stats():return jsonify(get_stats())

@app.get("/health")
def health():return jsonify({"ok":True})

if __name__=="__main__":
    start_scheduler()
    app.run(host=os.getenv("HOST","0.0.0.0"),port=int(os.getenv("PORT","5000")),debug=False)