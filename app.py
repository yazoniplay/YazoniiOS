import csv, io, os, sqlite3
from datetime import date, datetime
from functools import wraps
from flask import Flask, flash, g, redirect, render_template_string, request, session, url_for, send_file

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY","change-this-in-production")
DB_PATH=os.getenv("DATABASE_PATH","leadflow.db")
APP_PASSWORD=os.getenv("APP_PASSWORD","")
STATUSES=["New","Contacted","Qualified","Won","Lost"]

CSS="""<style>
:root{--bg:#070707;--card:#111;--line:#262626;--text:#f5f5f5;--muted:#999;--accent:#ff6900;--green:#55d187;--red:#ff6262}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#241100 0,#070707 40%);color:var(--text);font:15px Inter,system-ui,sans-serif}
a{color:inherit;text-decoration:none}.wrap{max-width:1150px;margin:auto;padding:24px}.nav{display:flex;justify-content:space-between;align-items:center;padding:10px 0 28px}.brand{font-weight:900;font-size:21px}.brand span{color:var(--accent)}.navlinks{display:flex;gap:15px;color:var(--muted);flex-wrap:wrap}.navlinks a:hover{color:white}
h1{font-size:34px;margin:8px 0}.sub{color:var(--muted);margin:0 0 24px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{background:#111;border:1px solid var(--line);border-radius:16px;padding:18px}.metric{font-size:28px;font-weight:900;margin-top:7px}.label{color:var(--muted);font-size:13px}
.toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:24px 0 14px}.btn{display:inline-block;border:1px solid var(--line);background:#171717;color:white;border-radius:10px;padding:10px 14px;cursor:pointer}.btn.primary{background:var(--accent);border-color:var(--accent);color:#111;font-weight:800}.btn.green{background:#15301f;border-color:#285c3c}.btn.danger{color:#ff8a8a}
table{width:100%;border-collapse:collapse;background:#111;border:1px solid var(--line);border-radius:16px;overflow:hidden}th,td{text-align:left;padding:13px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:12px;text-transform:uppercase}tr:last-child td{border:0}.pill{padding:5px 9px;border-radius:999px;background:#1d1d1d;font-size:12px}.overdue{color:var(--red)}.today{color:#ffc36b}
form{max-width:700px}.field{margin:14px 0}.field label{display:block;color:var(--muted);font-size:13px;margin-bottom:7px}.field input,.field select,.field textarea{width:100%;padding:11px 12px;background:#0c0c0c;color:white;border:1px solid var(--line);border-radius:10px;font:inherit}.field textarea{min-height:120px}.actions{display:flex;gap:10px;margin-top:18px}.flash{padding:11px 13px;border:1px solid #49301f;background:#1c1209;border-radius:10px;margin:10px 0}.empty{padding:35px;text-align:center;color:var(--muted)}.login{max-width:420px;margin:15vh auto}.right{text-align:right}
.notice{padding:14px;border:1px solid #30465a;background:#101a22;border-radius:12px;margin:14px 0}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:760px){.grid,.two{grid-template-columns:1fr 1fr}.navlinks{display:none}h1{font-size:28px}th:nth-child(4),td:nth-child(4){display:none}}
</style>"""

BASE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Yazoni LeadFlow</title>"""+CSS+"""</head><body><div class="wrap">
<nav class="nav"><a class="brand" href="{{url_for('dashboard')}}">Yazoni <span>LeadFlow</span></a><div class="navlinks"><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('leads')}}">Leads</a><a href="{{url_for('reminders')}}">Follow-ups</a><a href="{{url_for('import_leads')}}">Import</a><a href="{{url_for('new_lead')}}">+ Lead</a>{% if session.get('logged_in') %}<a href="{{url_for('logout')}}">Log out</a>{% endif %}</div></nav>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</div></body></html>"""

def db():
    if "db" not in g:
        g.db=sqlite3.connect(DB_PATH); g.db.row_factory=sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(exc):
    c=g.pop("db",None)
    if c:c.close()
def init_db():
    c=sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,company TEXT,email TEXT,value REAL DEFAULT 0,status TEXT NOT NULL DEFAULT 'New',follow_up TEXT,notes TEXT,created_at TEXT NOT NULL)""")
    c.commit();c.close()
def login_required(fn):
    @wraps(fn)
    def w(*a,**k):
        if not session.get("logged_in"): return redirect(url_for("login"))
        return fn(*a,**k)
    return w

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if APP_PASSWORD and request.form.get("password")==APP_PASSWORD:
            session["logged_in"]=True;return redirect(url_for("dashboard"))
        flash("Set APP_PASSWORD in the environment before using this app publicly." if not APP_PASSWORD else "Wrong password.")
    body=render_template_string("""<div class="login"><div class="card"><h1>LeadFlow</h1><p class="sub">Private sales workspace.</p><form method="post"><div class="field"><label>Password</label><input name="password" type="password" required autofocus></div><button class="btn primary">Sign in</button></form></div></div>""")
    return render_template_string(BASE,title="Login",body=body)
@app.route("/logout")
def logout(): session.clear();return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    c=db()
    total=c.execute("SELECT COUNT(*) n FROM leads").fetchone()["n"]
    pipeline=c.execute("SELECT COALESCE(SUM(value),0) n FROM leads WHERE status NOT IN ('Won','Lost')").fetchone()["n"]
    won=c.execute("SELECT COALESCE(SUM(value),0) n FROM leads WHERE status='Won'").fetchone()["n"]
    due=c.execute("SELECT COUNT(*) n FROM leads WHERE follow_up IS NOT NULL AND follow_up<=? AND status NOT IN ('Won','Lost')",(date.today().isoformat(),)).fetchone()["n"]
    recent=c.execute("SELECT * FROM leads ORDER BY id DESC LIMIT 8").fetchall()
    body=render_template_string("""<h1>Sales command center.</h1><p class="sub">Turn leads into organized follow-ups and revenue.</p>
<div class="grid"><div class="card"><div class="label">Total leads</div><div class="metric">{{total}}</div></div><div class="card"><div class="label">Open pipeline</div><div class="metric">€{{"%.0f"|format(pipeline)}}</div></div><div class="card"><div class="label">Won value</div><div class="metric">€{{"%.0f"|format(won)}}</div></div><div class="card"><div class="label">Follow-ups due</div><div class="metric">{{due}}</div></div></div>
<div class="toolbar"><h2>Recent leads</h2><div><a class="btn" href="{{url_for('import_leads')}}">Import CSV</a> <a class="btn primary" href="{{url_for('new_lead')}}">+ Add lead</a></div></div>
{% if recent %}<table><tr><th>Lead</th><th>Status</th><th>Value</th><th>Follow-up</th></tr>{%for x in recent%}<tr><td><a href="{{url_for('edit_lead',lead_id=x.id)}}"><b>{{x.name}}</b></a><br><span class="label">{{x.company or 'No company'}}</span></td><td><span class="pill">{{x.status}}</span></td><td>€{{"%.0f"|format(x.value or 0)}}</td><td>{{x.follow_up or '—'}}</td></tr>{%endfor%}</table>{%else%}<div class="card empty">No leads yet. Add or import your first leads.</div>{%endif%}""",total=total,pipeline=pipeline,won=won,due=due,recent=recent)
    return render_template_string(BASE,title="Dashboard",body=body)

@app.route("/leads")
@login_required
def leads():
    status=request.args.get("status","");q=request.args.get("q","").strip();sql="SELECT * FROM leads WHERE 1=1";p=[]
    if status in STATUSES:sql+=" AND status=?";p.append(status)
    if q:sql+=" AND (name LIKE ? OR company LIKE ? OR email LIKE ?)";like=f"%{q}%";p += [like,like,like]
    rows=db().execute(sql+" ORDER BY id DESC",p).fetchall()
    body=render_template_string("""<div class="toolbar"><div><h1>Leads</h1><p class="sub">Your sales pipeline.</p></div><a class="btn primary" href="{{url_for('new_lead')}}">+ Add lead</a></div>
<form method="get" style="max-width:none;display:flex;gap:8px;margin-bottom:14px"><input name="q" value="{{q}}" placeholder="Search name, company or email" style="flex:1;padding:11px;background:#0c0c0c;color:white;border:1px solid #242424;border-radius:10px"><select name="status" style="padding:11px;background:#0c0c0c;color:white;border:1px solid #242424;border-radius:10px"><option value="">All statuses</option>{%for s in statuses%}<option value="{{s}}" {%if status==s%}selected{%endif%}>{{s}}</option>{%endfor%}</select><button class="btn">Search</button></form>
{%if rows%}<table><tr><th>Lead</th><th>Company</th><th>Status</th><th>Value</th><th>Follow-up</th><th></th></tr>{%for x in rows%}<tr><td><a href="{{url_for('edit_lead',lead_id=x.id)}}"><b>{{x.name}}</b></a><br><span class="label">{{x.email or ''}}</span></td><td>{{x.company or '—'}}</td><td><span class="pill">{{x.status}}</span></td><td>€{{"%.0f"|format(x.value or 0)}}</td><td>{{x.follow_up or '—'}}</td><td>{%if x.email%}<a class="btn" href="mailto:{{x.email}}?subject=Following%20up">Email</a>{%endif%}</td></tr>{%endfor%}</table>{%else%}<div class="card empty">No matching leads.</div>{%endif%}""",rows=rows,statuses=STATUSES,status=status,q=q)
    return render_template_string(BASE,title="Leads",body=body)

@app.route("/reminders")
@login_required
def reminders():
    today=date.today().isoformat()
    rows=db().execute("SELECT * FROM leads WHERE follow_up IS NOT NULL AND status NOT IN ('Won','Lost') ORDER BY follow_up ASC").fetchall()
    body=render_template_string("""<h1>Follow-ups</h1><p class="sub">Never let a warm lead disappear because you forgot to follow up.</p>
{%if rows%}<table><tr><th>Lead</th><th>Company</th><th>Due</th><th>Status</th><th>Action</th></tr>{%for x in rows%}<tr><td><b>{{x.name}}</b></td><td>{{x.company or '—'}}</td><td class="{{'overdue' if x.follow_up<today else ('today' if x.follow_up==today else '')}}">{{x.follow_up}}</td><td>{{x.status}}</td><td>{%if x.email%}<a class="btn" href="mailto:{{x.email}}?subject=Following%20up">Email</a>{%endif%} <a class="btn" href="{{url_for('edit_lead',lead_id=x.id)}}">Update</a></td></tr>{%endfor%}</table>{%else%}<div class="card empty">No scheduled follow-ups.</div>{%endif%}""",rows=rows,today=today)
    return render_template_string(BASE,title="Follow-ups",body=body)

FORM="""<h1>{{'Edit lead' if lead else 'Add a lead'}}</h1><p class="sub">Capture the information needed to close the deal.</p>
<form method="post"><div class="field"><label>Name *</label><input name="name" value="{{lead.name if lead else ''}}" required></div><div class="two"><div class="field"><label>Company</label><input name="company" value="{{lead.company if lead else ''}}"></div><div class="field"><label>Email</label><input name="email" type="email" value="{{lead.email if lead else ''}}"></div></div><div class="two"><div class="field"><label>Potential value (€)</label><input name="value" type="number" min="0" step="1" value="{{lead.value if lead else 0}}"></div><div class="field"><label>Status</label><select name="status">{%for s in statuses%}<option {%if lead and lead.status==s%}selected{%endif%}>{{s}}</option>{%endfor%}</select></div></div><div class="field"><label>Next follow-up</label><input name="follow_up" type="date" value="{{lead.follow_up if lead else ''}}"></div><div class="field"><label>Notes</label><textarea name="notes">{{lead.notes if lead else ''}}</textarea></div><div class="actions"><button class="btn primary">Save lead</button><a class="btn" href="{{url_for('leads')}}">Cancel</a></div></form>
{%if lead%}<form method="post" action="{{url_for('delete_lead',lead_id=lead.id)}}" onsubmit="return confirm('Delete this lead?')"><button class="btn danger">Delete lead</button></form>{%endif%}"""

@app.route("/leads/new",methods=["GET","POST"])
@login_required
def new_lead():
    if request.method=="POST":
        db().execute("INSERT INTO leads(name,company,email,value,status,follow_up,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",(request.form["name"].strip(),request.form.get("company","").strip(),request.form.get("email","").strip(),float(request.form.get("value") or 0),request.form.get("status","New"),request.form.get("follow_up") or None,request.form.get("notes","").strip(),datetime.utcnow().isoformat()));db().commit();flash("Lead added.");return redirect(url_for("leads"))
    return render_template_string(BASE,title="Add lead",body=render_template_string(FORM,lead=None,statuses=STATUSES))
@app.route("/leads/<int:lead_id>",methods=["GET","POST"])
@login_required
def edit_lead(lead_id):
    lead=db().execute("SELECT * FROM leads WHERE id=?",(lead_id,)).fetchone()
    if not lead:return "Lead not found",404
    if request.method=="POST":
        db().execute("UPDATE leads SET name=?,company=?,email=?,value=?,status=?,follow_up=?,notes=? WHERE id=?",(request.form["name"].strip(),request.form.get("company","").strip(),request.form.get("email","").strip(),float(request.form.get("value") or 0),request.form.get("status","New"),request.form.get("follow_up") or None,request.form.get("notes","").strip(),lead_id));db().commit();flash("Lead updated.");return redirect(url_for("leads"))
    return render_template_string(BASE,title="Edit lead",body=render_template_string(FORM,lead=lead,statuses=STATUSES))
@app.post("/leads/<int:lead_id>/delete")
@login_required
def delete_lead(lead_id):
    db().execute("DELETE FROM leads WHERE id=?",(lead_id,));db().commit();flash("Lead deleted.");return redirect(url_for("leads"))

@app.route("/import",methods=["GET","POST"])
@login_required
def import_leads():
    if request.method=="POST":
        f=request.files.get("file")
        if not f or not f.filename.lower().endswith(".csv"):flash("Upload a CSV file.");return redirect(url_for("import_leads"))
        try:
            text=f.read().decode("utf-8-sig");reader=csv.DictReader(io.StringIO(text));count=0
            for r in reader:
                name=(r.get("name") or r.get("Name") or "").strip()
                if not name:continue
                db().execute("INSERT INTO leads(name,company,email,value,status,follow_up,notes,created_at) VALUES(?,?,?,?,?,?,?,?)",(name,(r.get("company") or r.get("Company") or "").strip(),(r.get("email") or r.get("Email") or "").strip(),float((r.get("value") or "0").replace(",","") or 0),((r.get("status") or "New").strip() if (r.get("status") or "New").strip() in STATUSES else "New"),(r.get("follow_up") or "").strip() or None,(r.get("notes") or "").strip(),datetime.utcnow().isoformat()));count+=1
            db().commit();flash(f"Imported {count} leads.");return redirect(url_for("leads"))
        except Exception as e:flash(f"Import failed: {e}")
    body=render_template_string("""<h1>Import leads</h1><p class="sub">Upload a CSV and turn an existing spreadsheet into your pipeline.</p><div class="notice"><b>CSV columns:</b> name, company, email, value, status, follow_up, notes</div><form method="post" enctype="multipart/form-data"><div class="field"><label>CSV file</label><input type="file" name="file" accept=".csv" required></div><button class="btn primary">Import leads</button></form>""")
    return render_template_string(BASE,title="Import",body=body)

@app.route("/export.csv")
@login_required
def export_csv():
    rows=db().execute("SELECT name,company,email,value,status,follow_up,notes,created_at FROM leads ORDER BY id DESC").fetchall()
    out=io.StringIO();w=csv.writer(out);w.writerow(["name","company","email","value","status","follow_up","notes","created_at"])
    for r in rows:w.writerow([r[k] for k in r.keys()])
    mem=io.BytesIO(out.getvalue().encode());return send_file(mem,mimetype="text/csv",as_attachment=True,download_name="leadflow-leads.csv")

with app.app_context():init_db()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
