import csv, io, os, secrets, sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from urllib.parse import urljoin

from flask import Flask, flash, g, redirect, render_template_string, request, session, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
DB_PATH = os.getenv("DATABASE_PATH", "leadflow.db")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_TEAM_PRICE_ID = os.getenv("STRIPE_TEAM_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STATUSES = ["New", "Contacted", "Qualified", "Won", "Lost"]
PLANS = {
    "free": {"name": "Free", "price": "€0", "limit": 50, "seats": 1},
    "pro": {"name": "Pro", "price": "€19/mo", "limit": 1000, "seats": 3},
    "team": {"name": "Team", "price": "€49/mo", "limit": 10000, "seats": 15},
}

CSS = """<style>
:root{--bg:#070707;--card:#111;--line:#262626;--text:#f5f5f5;--muted:#999;--accent:#ff6900;--green:#55d187;--red:#ff6262}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at top right,#241100 0,#070707 40%);color:var(--text);font:15px Inter,system-ui,sans-serif}
a{color:inherit;text-decoration:none}.wrap{max-width:1180px;margin:auto;padding:24px}.nav{display:flex;justify-content:space-between;align-items:center;padding:10px 0 28px}.brand{font-weight:900;font-size:21px}.brand span{color:var(--accent)}.navlinks{display:flex;gap:14px;color:var(--muted);flex-wrap:wrap}.navlinks a:hover{color:white}
h1{font-size:34px;margin:8px 0}.sub{color:var(--muted);margin:0 0 24px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{background:#111;border:1px solid var(--line);border-radius:16px;padding:18px}.metric{font-size:28px;font-weight:900;margin-top:7px}.label{color:var(--muted);font-size:13px}
.toolbar{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:24px 0 14px}.btn{display:inline-block;border:1px solid var(--line);background:#171717;color:white;border-radius:10px;padding:10px 14px;cursor:pointer}.btn.primary{background:var(--accent);border-color:var(--accent);color:#111;font-weight:800}.btn.danger{color:#ff8a8a}
table{width:100%;border-collapse:collapse;background:#111;border:1px solid var(--line);border-radius:16px;overflow:hidden}th,td{text-align:left;padding:13px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-size:12px;text-transform:uppercase}tr:last-child td{border:0}.pill{padding:5px 9px;border-radius:999px;background:#1d1d1d;font-size:12px}.overdue{color:var(--red)}.today{color:#ffc36b}
form{max-width:700px}.field{margin:14px 0}.field label{display:block;color:var(--muted);font-size:13px;margin-bottom:7px}.field input,.field select,.field textarea{width:100%;padding:11px 12px;background:#0c0c0c;color:white;border:1px solid var(--line);border-radius:10px;font:inherit}.field textarea{min-height:120px}.actions{display:flex;gap:10px;margin-top:18px}.flash{padding:11px 13px;border:1px solid #49301f;background:#1c1209;border-radius:10px;margin:10px 0}.empty{padding:35px;text-align:center;color:var(--muted)}.login{max-width:460px;margin:10vh auto}
.notice{padding:14px;border:1px solid #30465a;background:#101a22;border-radius:12px;margin:14px 0}.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}.three{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.plan{display:flex;flex-direction:column;gap:10px;min-height:220px}.plan h2{margin:0}.price{font-size:30px;font-weight:900}.muted{color:var(--muted)}.tag{display:inline-block;background:#2a180c;color:#ffad70;padding:5px 8px;border-radius:999px;font-size:12px}
@media(max-width:760px){.grid,.two,.three{grid-template-columns:1fr 1fr}.navlinks{display:none}h1{font-size:28px}th:nth-child(4),td:nth-child(4){display:none}}
@media(max-width:520px){.grid,.two,.three{grid-template-columns:1fr}}
</style>"""

BASE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Yazoni LeadFlow</title>""" + CSS + """</head><body><div class="wrap">
<nav class="nav"><a class="brand" href="{{url_for('dashboard')}}"><b>Yazoni</b> <span>LeadFlow</span></a><div class="navlinks">
{% if session.get('user_id') or session.get('legacy_access') %}<a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('leads')}}">Leads</a><a href="{{url_for('reminders')}}">Follow-ups</a><a href="{{url_for('team')}}">Team</a><a href="{{url_for('billing')}}">Billing</a><a href="{{url_for('import_leads')}}">Import</a><a href="{{url_for('new_lead')}}">+ Lead</a><a href="{{url_for('logout')}}">Log out</a>{% endif %}
</div></nav>{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}</div></body></html>"""

AUTH_BASE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Yazoni LeadFlow</title>""" + CSS + """</head><body><div class="wrap">{{body|safe}}</div></body></html>"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    c = g.pop("db", None)
    if c:
        c.close()

def column_exists(table, column):
    return any(r["name"] == column for r in db().execute(f"PRAGMA table_info({table})").fetchall())

def init_db():
    c = sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS workspaces(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,plan TEXT NOT NULL DEFAULT 'free',stripe_customer_id TEXT,stripe_subscription_id TEXT,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS memberships(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,workspace_id INTEGER NOT NULL,role TEXT NOT NULL DEFAULT 'member',UNIQUE(user_id,workspace_id))")
    c.execute("CREATE TABLE IF NOT EXISTS invites(id INTEGER PRIMARY KEY AUTOINCREMENT,workspace_id INTEGER NOT NULL,email TEXT,token TEXT UNIQUE NOT NULL,role TEXT NOT NULL DEFAULT 'member',expires_at TEXT NOT NULL,created_at TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,company TEXT,email TEXT,value REAL DEFAULT 0,status TEXT NOT NULL DEFAULT 'New',follow_up TEXT,notes TEXT,created_at TEXT NOT NULL)")
    c.commit()
    c.close()
    with app.app_context():
        if not column_exists("leads", "workspace_id"):
            db().execute("ALTER TABLE leads ADD COLUMN workspace_id INTEGER")
            db().commit()
        count = db().execute("SELECT COUNT(*) n FROM workspaces").fetchone()["n"]
        if count == 0:
            db().execute("INSERT INTO workspaces(name,plan,created_at) VALUES(?,?,?)", ("Default Workspace","free",datetime.utcnow().isoformat()))
            db().commit()
        wid = db().execute("SELECT id FROM workspaces ORDER BY id LIMIT 1").fetchone()["id"]
        db().execute("UPDATE leads SET workspace_id=? WHERE workspace_id IS NULL", (wid,))
        db().commit()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

def current_workspace():
    wid = session.get("workspace_id")
    if not wid:
        return None
    return db().execute("SELECT * FROM workspaces WHERE id=?", (wid,)).fetchone()

def current_role():
    u = current_user()
    w = current_workspace()
    if not u or not w:
        return None
    row = db().execute("SELECT role FROM memberships WHERE user_id=? AND workspace_id=?", (u["id"], w["id"])).fetchone()
    return row["role"] if row else None

def login_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if not session.get("user_id") and not session.get("legacy_access"):
            return redirect(url_for("login"))
        return fn(*a, **k)
    return w

def workspace_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if session.get("legacy_access") and not session.get("workspace_id"):
            session["workspace_id"] = db().execute("SELECT id FROM workspaces ORDER BY id LIMIT 1").fetchone()["id"]
        if not session.get("workspace_id"):
            return redirect(url_for("login"))
        return fn(*a, **k)
    return w

def owner_required(fn):
    @wraps(fn)
    def w(*a, **k):
        if current_role() != "owner":
            flash("Owner access required.")
            return redirect(url_for("dashboard"))
        return fn(*a, **k)
    return w

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        workspace_name = request.form.get("workspace","").strip() or f"{name}'s Workspace"
        if len(name) < 2 or "@" not in email or len(password) < 8:
            flash("Use a name, valid email, and password with at least 8 characters.")
        elif db().execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
            flash("An account with that email already exists.")
        else:
            now = datetime.utcnow().isoformat()
            cur = db()
            cur.execute("INSERT INTO users(email,password_hash,name,created_at) VALUES(?,?,?,?)", (email,generate_password_hash(password),name,now))
            uid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
            cur.execute("INSERT INTO workspaces(name,plan,created_at) VALUES(?,?,?)", (workspace_name,"free",now))
            wid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
            cur.execute("INSERT INTO memberships(user_id,workspace_id,role) VALUES(?,?,?)", (uid,wid,"owner"))
            cur.commit()
            session.clear(); session["user_id"]=uid; session["workspace_id"]=wid
            flash("Workspace created.")
            return redirect(url_for("dashboard"))
    body = render_template_string("""<div class="login"><div class="card"><h1>Create LeadFlow</h1><p class="sub">Create your account and your first workspace.</p>
<form method="post"><div class="field"><label>Your name</label><input name="name" required></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" minlength="8" required></div><div class="field"><label>Workspace name</label><input name="workspace" placeholder="Acme Sales"></div><button class="btn primary">Create account</button></form><p class="sub">Already have an account? <a href="{{url_for('login')}}">Sign in</a></p></div></div>""")
    return render_template_string(AUTH_BASE,title="Sign up",body=body)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            memberships = db().execute("SELECT workspace_id FROM memberships WHERE user_id=? ORDER BY id", (user["id"],)).fetchall()
            if memberships:
                session.clear(); session["user_id"]=user["id"]; session["workspace_id"]=memberships[0]["workspace_id"]
                return redirect(url_for("dashboard"))
        if APP_PASSWORD and password == APP_PASSWORD:
            wid = db().execute("SELECT id FROM workspaces ORDER BY id LIMIT 1").fetchone()["id"]
            session.clear(); session["legacy_access"]=True; session["workspace_id"]=wid
            return redirect(url_for("dashboard"))
        flash("Wrong email or password.")
    body = render_template_string("""<div class="login"><div class="card"><h1>LeadFlow</h1><p class="sub">Sales operations for small teams.</p>
<form method="post"><div class="field"><label>Email</label><input name="email" type="email" required autofocus></div><div class="field"><label>Password</label><input name="password" type="password" required></div><button class="btn primary">Sign in</button></form>
<p class="sub" style="margin-top:18px">New here? <a href="{{url_for('signup')}}">Create a workspace</a></p>
{% if legacy %}<div class="notice">Legacy password access is enabled for this deployment.</div>{% endif %}</div></div>""", legacy=bool(APP_PASSWORD))
    return render_template_string(AUTH_BASE,title="Login",body=body)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
@workspace_required
def dashboard():
    wid = session["workspace_id"]; c=db()
    total=c.execute("SELECT COUNT(*) n FROM leads WHERE workspace_id=?", (wid,)).fetchone()["n"]
    pipeline=c.execute("SELECT COALESCE(SUM(value),0) n FROM leads WHERE workspace_id=? AND status NOT IN ('Won','Lost')",(wid,)).fetchone()["n"]
    won=c.execute("SELECT COALESCE(SUM(value),0) n FROM leads WHERE workspace_id=? AND status='Won'",(wid,)).fetchone()["n"]
    due=c.execute("SELECT COUNT(*) n FROM leads WHERE workspace_id=? AND follow_up IS NOT NULL AND follow_up<=? AND status NOT IN ('Won','Lost')",(wid,date.today().isoformat())).fetchone()["n"]
    recent=c.execute("SELECT * FROM leads WHERE workspace_id=? ORDER BY id DESC LIMIT 8",(wid,)).fetchall()
    w=current_workspace()
    body=render_template_string("""<h1>Sales command center.</h1><p class="sub">{{w.name}} · <span class="tag">{{plan}}</span></p>
<div class="grid"><div class="card"><div class="label">Total leads</div><div class="metric">{{total}}</div></div><div class="card"><div class="label">Open pipeline</div><div class="metric">€{{"%.0f"|format(pipeline)}}</div></div><div class="card"><div class="label">Won value</div><div class="metric">€{{"%.0f"|format(won)}}</div></div><div class="card"><div class="label">Follow-ups due</div><div class="metric">{{due}}</div></div></div>
<div class="toolbar"><h2>Recent leads</h2><div><a class="btn" href="{{url_for('import_leads')}}">Import CSV</a> <a class="btn primary" href="{{url_for('new_lead')}}">+ Add lead</a></div></div>
{% if recent %}<table><tr><th>Lead</th><th>Status</th><th>Value</th><th>Follow-up</th></tr>{%for x in recent%}<tr><td><a href="{{url_for('edit_lead',lead_id=x.id)}}"><b>{{x.name}}</b></a><br><span class="label">{{x.company or 'No company'}}</span></td><td><span class="pill">{{x.status}}</span></td><td>€{{"%.0f"|format(x.value or 0)}}</td><td>{{x.follow_up or '—'}}</td></tr>{%endfor%}</table>{%else%}<div class="card empty">No leads yet. Add or import your first leads.</div>{%endif%}""", total=total,pipeline=pipeline,won=won,due=due,recent=recent,w=w,plan=PLANS.get(w["plan"],PLANS["free"])["name"])
    return render_template_string(BASE,title="Dashboard",body=body)

@app.route("/leads")
@login_required
@workspace_required
def leads():
    status=request.args.get("status",""); q=request.args.get("q","").strip(); sql="SELECT * FROM leads WHERE workspace_id=?"; p=[session["workspace_id"]]
    if status in STATUSES: sql+=" AND status=?"; p.append(status)
    if q: sql+=" AND (name LIKE ? OR company LIKE ? OR email LIKE ?)"; like=f"%{q}%"; p += [like,like,like]
    rows=db().execute(sql+" ORDER BY id DESC",p).fetchall()
    body=render_template_string("""<div class="toolbar"><div><h1>Leads</h1><p class="sub">Your team's sales pipeline.</p></div><a class="btn primary" href="{{url_for('new_lead')}}">+ Add lead</a></div>
<form method="get" style="max-width:none;display:flex;gap:8px;margin-bottom:14px"><input name="q" value="{{q}}" placeholder="Search name, company or email" style="flex:1;padding:11px;background:#0c0c0c;color:white;border:1px solid #242424;border-radius:10px"><select name="status" style="padding:11px;background:#0c0c0c;color:white;border:1px solid #242424;border-radius:10px"><option value="">All statuses</option>{%for s in statuses%}<option value="{{s}}" {%if status==s%}selected{%endif%}>{{s}}</option>{%endfor%}</select><button class="btn">Search</button></form>
{%if rows%}<table><tr><th>Lead</th><th>Company</th><th>Status</th><th>Value</th><th>Follow-up</th><th></th></tr>{%for x in rows%}<tr><td><a href="{{url_for('edit_lead',lead_id=x.id)}}"><b>{{x.name}}</b></a><br><span class="label">{{x.email or ''}}</span></td><td>{{x.company or '—'}}</td><td><span class="pill">{{x.status}}</span></td><td>€{{"%.0f"|format(x.value or 0)}}</td><td>{{x.follow_up or '—'}}</td><td>{%if x.email%}<a class="btn" href="mailto:{{x.email}}?subject=Following%20up">Email</a>{%endif%}</td></tr>{%endfor%}</table>{%else%}<div class="card empty">No matching leads.</div>{%endif%}""",rows=rows,statuses=STATUSES,status=status,q=q)
    return render_template_string(BASE,title="Leads",body=body)

@app.route("/reminders")
@login_required
@workspace_required
def reminders():
    today=date.today().isoformat(); rows=db().execute("SELECT * FROM leads WHERE workspace_id=? AND follow_up IS NOT NULL AND status NOT IN ('Won','Lost') ORDER BY follow_up ASC",(session["workspace_id"],)).fetchall()
    body=render_template_string("""<h1>Follow-ups</h1><p class="sub">Never let a warm lead disappear because you forgot to follow up.</p>
{%if rows%}<table><tr><th>Lead</th><th>Company</th><th>Due</th><th>Status</th><th>Action</th></tr>{%for x in rows%}<tr><td><b>{{x.name}}</b></td><td>{{x.company or '—'}}</td><td class="{{'overdue' if x.follow_up<today else ('today' if x.follow_up==today else '')}}">{{x.follow_up}}</td><td>{{x.status}}</td><td>{%if x.email%}<a class="btn" href="mailto:{{x.email}}?subject=Following%20up">Email</a>{%endif%} <a class="btn" href="{{url_for('edit_lead',lead_id=x.id)}}">Update</a></td></tr>{%endfor%}</table>{%else%}<div class="card empty">No scheduled follow-ups.</div>{%endif%}""",rows=rows,today=today)
    return render_template_string(BASE,title="Follow-ups",body=body)

FORM = """<h1>{{'Edit lead' if lead else 'Add a lead'}}</h1><p class="sub">Capture the information needed to close the deal.</p>
<form method="post"><div class="field"><label>Name *</label><input name="name" value="{{lead.name if lead else ''}}" required></div><div class="two"><div class="field"><label>Company</label><input name="company" value="{{lead.company if lead else ''}}"></div><div class="field"><label>Email</label><input name="email" type="email" value="{{lead.email if lead else ''}}"></div></div><div class="two"><div class="field"><label>Potential value (€)</label><input name="value" type="number" min="0" step="1" value="{{lead.value if lead else 0}}"></div><div class="field"><label>Status</label><select name="status">{%for s in statuses%}<option {%if lead and lead.status==s%}selected{%endif%}>{{s}}</option>{%endfor%}</select></div></div><div class="field"><label>Next follow-up</label><input name="follow_up" type="date" value="{{lead.follow_up if lead else ''}}"></div><div class="field"><label>Notes</label><textarea name="notes">{{lead.notes if lead else ''}}</textarea></div><div class="actions"><button class="btn primary">Save lead</button><a class="btn" href="{{url_for('leads')}}">Cancel</a></div></form>
{%if lead%}<form method="post" action="{{url_for('delete_lead',lead_id=lead.id)}}" onsubmit="return confirm('Delete this lead?')"><button class="btn danger">Delete lead</button></form>{%endif%}"""

def lead_limit_reached():
    w=current_workspace()
    limit=PLANS.get(w["plan"],PLANS["free"])["limit"]
    count=db().execute("SELECT COUNT(*) n FROM leads WHERE workspace_id=?",(w["id"],)).fetchone()["n"]
    return count >= limit

@app.route("/leads/new",methods=["GET","POST"])
@login_required
@workspace_required
def new_lead():
    if request.method=="POST":
        if lead_limit_reached():
            flash("Your plan has reached its lead limit. Upgrade from Billing.")
            return redirect(url_for("billing"))
        db().execute("INSERT INTO leads(workspace_id,name,company,email,value,status,follow_up,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(session["workspace_id"],request.form["name"].strip(),request.form.get("company","").strip(),request.form.get("email","").strip(),float(request.form.get("value") or 0),request.form.get("status","New"),request.form.get("follow_up") or None,request.form.get("notes","").strip(),datetime.utcnow().isoformat()))
        db().commit(); flash("Lead added."); return redirect(url_for("leads"))
    return render_template_string(BASE,title="Add lead",body=render_template_string(FORM,lead=None,statuses=STATUSES))

@app.route("/leads/<int:lead_id>",methods=["GET","POST"])
@login_required
@workspace_required
def edit_lead(lead_id):
    lead=db().execute("SELECT * FROM leads WHERE id=? AND workspace_id=?",(lead_id,session["workspace_id"])).fetchone()
    if not lead:return "Lead not found",404
    if request.method=="POST":
        db().execute("UPDATE leads SET name=?,company=?,email=?,value=?,status=?,follow_up=?,notes=? WHERE id=? AND workspace_id=?",(request.form["name"].strip(),request.form.get("company","").strip(),request.form.get("email","").strip(),float(request.form.get("value") or 0),request.form.get("status","New"),request.form.get("follow_up") or None,request.form.get("notes","").strip(),lead_id,session["workspace_id"]))
        db().commit(); flash("Lead updated."); return redirect(url_for("leads"))
    return render_template_string(BASE,title="Edit lead",body=render_template_string(FORM,lead=lead,statuses=STATUSES))

@app.post("/leads/<int:lead_id>/delete")
@login_required
@workspace_required
def delete_lead(lead_id):
    db().execute("DELETE FROM leads WHERE id=? AND workspace_id=?",(lead_id,session["workspace_id"]));db().commit();flash("Lead deleted.");return redirect(url_for("leads"))

@app.route("/import",methods=["GET","POST"])
@login_required
@workspace_required
def import_leads():
    if request.method=="POST":
        f=request.files.get("file")
        if not f or not f.filename.lower().endswith(".csv"): flash("Upload a CSV file."); return redirect(url_for("import_leads"))
        try:
            text=f.read().decode("utf-8-sig"); reader=csv.DictReader(io.StringIO(text)); count=0
            for r in reader:
                if lead_limit_reached(): break
                name=(r.get("name") or r.get("Name") or "").strip()
                if not name: continue
                status=((r.get("status") or "New").strip() if (r.get("status") or "New").strip() in STATUSES else "New")
                db().execute("INSERT INTO leads(workspace_id,name,company,email,value,status,follow_up,notes,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(session["workspace_id"],name,(r.get("company") or r.get("Company") or "").strip(),(r.get("email") or r.get("Email") or "").strip(),float((r.get("value") or "0").replace(",","") or 0),status,(r.get("follow_up") or "").strip() or None,(r.get("notes") or "").strip(),datetime.utcnow().isoformat()));count+=1
            db().commit(); flash(f"Imported {count} leads."); return redirect(url_for("leads"))
        except Exception as e: flash(f"Import failed: {e}")
    body=render_template_string("""<h1>Import leads</h1><p class="sub">Upload a CSV and turn an existing spreadsheet into your pipeline.</p><div class="notice"><b>CSV columns:</b> name, company, email, value, status, follow_up, notes</div><form method="post" enctype="multipart/form-data"><div class="field"><label>CSV file</label><input type="file" name="file" accept=".csv" required></div><button class="btn primary">Import leads</button></form>""")
    return render_template_string(BASE,title="Import",body=body)

@app.route("/export.csv")
@login_required
@workspace_required
def export_csv():
    rows=db().execute("SELECT name,company,email,value,status,follow_up,notes,created_at FROM leads WHERE workspace_id=? ORDER BY id DESC",(session["workspace_id"],)).fetchall()
    out=io.StringIO(); w=csv.writer(out); w.writerow(["name","company","email","value","status","follow_up","notes","created_at"])
    for r in rows:w.writerow([r[k] for k in r.keys()])
    mem=io.BytesIO(out.getvalue().encode()); return send_file(mem,mimetype="text/csv",as_attachment=True,download_name="leadflow-leads.csv")

@app.route("/team",methods=["GET","POST"])
@login_required
@workspace_required
def team():
    if request.method=="POST":
        if current_role()!="owner": flash("Only the workspace owner can invite members."); return redirect(url_for("team"))
        email=request.form.get("email","").strip().lower(); role=request.form.get("role","member")
        w=current_workspace(); seats=PLANS.get(w["plan"],PLANS["free"])["seats"]
        members=db().execute("SELECT COUNT(*) n FROM memberships WHERE workspace_id=?",(w["id"],)).fetchone()["n"]
        if members>=seats: flash("Your plan has reached its seat limit."); return redirect(url_for("billing"))
        if not email or "@" not in email: flash("Enter a valid email."); return redirect(url_for("team"))
        token=secrets.token_urlsafe(24); exp=(datetime.utcnow()+timedelta(days=3)).isoformat()
        db().execute("INSERT INTO invites(workspace_id,email,token,role,expires_at,created_at) VALUES(?,?,?,?,?,?)",(w["id"],email,token,role,exp,datetime.utcnow().isoformat()));db().commit()
        link=url_for("accept_invite",token=token,_external=True)
        flash("Invite created. Share this link with the teammate: "+link)
        return redirect(url_for("team"))
    w=current_workspace(); members=db().execute("SELECT u.name,u.email,m.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? ORDER BY m.id",(w["id"],)).fetchall()
    invites=db().execute("SELECT email,role,expires_at,token FROM invites WHERE workspace_id=? ORDER BY id DESC LIMIT 10",(w["id"],)).fetchall()
    body=render_template_string("""<div class="toolbar"><div><h1>Team</h1><p class="sub">{{w.name}} · {{members|length}} member(s)</p></div></div>
<div class="two"><div class="card"><h2>Members</h2>{%for m in members%}<p><b>{{m.name}}</b><br><span class="muted">{{m.email}} · {{m.role}}</span></p>{%else%}<p class="muted">No members yet.</p>{%endfor%}</div>
<div class="card"><h2>Invite a teammate</h2>{%if role=='owner'%}<form method="post"><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Role</label><select name="role"><option value="member">Member</option><option value="owner">Owner</option></select></div><button class="btn primary">Create invite link</button></form>{%else%}<p class="muted">Only the workspace owner can create invites.</p>{%endif%}</div></div>
{%if invites%}<div class="toolbar"><h2>Recent invites</h2></div><table><tr><th>Email</th><th>Role</th><th>Expires</th><th>Invite link</th></tr>{%for i in invites%}<tr><td>{{i.email}}</td><td>{{i.role}}</td><td>{{i.expires_at[:10]}}</td><td><a class="btn" href="{{url_for('accept_invite',token=i.token)}}">Open invite</a></td></tr>{%endfor%}</table>{%endif%}""",w=w,members=members,invites=invites,role=current_role())
    return render_template_string(BASE,title="Team",body=body)

@app.route("/invite/<token>",methods=["GET","POST"])
def accept_invite(token):
    inv=db().execute("SELECT * FROM invites WHERE token=?",(token,)).fetchone()
    if not inv or inv["expires_at"] < datetime.utcnow().isoformat(): return "Invite expired or not found",404
    if not session.get("user_id"):
        flash("Create or sign in to an account first, then open the invite again.")
        return redirect(url_for("login"))
    user=current_user()
    if request.method=="POST":
        if db().execute("SELECT id FROM memberships WHERE user_id=? AND workspace_id=?",(user["id"],inv["workspace_id"])).fetchone():
            flash("You are already a member."); return redirect(url_for("dashboard"))
        db().execute("INSERT INTO memberships(user_id,workspace_id,role) VALUES(?,?,?)",(user["id"],inv["workspace_id"],inv["role"]));db().execute("DELETE FROM invites WHERE id=?",(inv["id"],));db().commit()
        session["workspace_id"]=inv["workspace_id"];flash("You joined the workspace.");return redirect(url_for("dashboard"))
    body=render_template_string("""<div class="login"><div class="card"><h1>Join workspace</h1><p class="sub">You were invited to join this LeadFlow workspace.</p><form method="post"><button class="btn primary">Join workspace</button></form></div></div>""")
    return render_template_string(AUTH_BASE,title="Join",body=body)

@app.route("/switch/<int:workspace_id>")
@login_required
def switch_workspace(workspace_id):
    uid=session.get("user_id")
    if uid and db().execute("SELECT id FROM memberships WHERE user_id=? AND workspace_id=?",(uid,workspace_id)).fetchone():
        session["workspace_id"]=workspace_id
    return redirect(url_for("dashboard"))

@app.route("/billing")
@login_required
@workspace_required
def billing():
    w=current_workspace()
    body=render_template_string("""<h1>Billing</h1><p class="sub">Choose the workspace plan that fits your sales operation.</p>
<div class="three">{%for key,p in plans.items()%}<div class="card plan"><span class="tag">{{'Current plan' if key==w.plan else key|upper}}</span><h2>{{p.name}}</h2><div class="price">{{p.price}}</div><div class="muted">Up to {{p.limit}} leads · {{p.seats}} seat(s)</div>{%if key==w.plan%}<button class="btn" disabled>Active</button>{%elif key!='free'%}<a class="btn primary" href="{{url_for('checkout',plan=key)}}">Upgrade to {{p.name}}</a>{%endif%}</div>{%endfor%}</div>
<div class="notice" style="margin-top:20px"><b>Stripe:</b> Checkout is ready when Stripe environment variables are configured. The app does not store card details.</div>""",plans=PLANS,w=w)
    return render_template_string(BASE,title="Billing",body=body)

@app.route("/checkout/<plan>")
@login_required
@workspace_required
def checkout(plan):
    if plan not in ("pro","team"): return redirect(url_for("billing"))
    if not STRIPE_SECRET_KEY: flash("Stripe is not configured yet. Add STRIPE_SECRET_KEY and the matching price ID in your deployment settings."); return redirect(url_for("billing"))
    price_id=STRIPE_PRO_PRICE_ID if plan=="pro" else STRIPE_TEAM_PRICE_ID
    if not price_id: flash(f"Missing Stripe price ID for {plan}."); return redirect(url_for("billing"))
    try:
        import stripe
        stripe.api_key=STRIPE_SECRET_KEY
        u=current_user()
        if not u: flash("A full account is required for checkout."); return redirect(url_for("login"))
        checkout_session=stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price":price_id,"quantity":1}],
            customer_email=u["email"],
            success_url=url_for("billing_success",plan=plan,_external=True),
            cancel_url=url_for("billing",_external=True),
            metadata={"workspace_id":str(session["workspace_id"]),"plan":plan},
            subscription_data={"metadata":{"workspace_id":str(session["workspace_id"]),"plan":plan}},
        )
        return redirect(checkout_session.url)
    except Exception as e:
        flash("Stripe checkout could not be started: "+str(e))
        return redirect(url_for("billing"))

@app.post("/stripe/webhook")
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        return "Webhook secret not configured", 503
    try:
        import stripe
        event = stripe.Webhook.construct_event(request.data, request.headers.get("Stripe-Signature",""), STRIPE_WEBHOOK_SECRET)
    except Exception:
        return "Invalid webhook", 400
    obj = event.get("data", {}).get("object", {})
    typ = event.get("type", "")
    metadata = obj.get("metadata", {}) or {}
    wid = metadata.get("workspace_id")
    if typ == "checkout.session.completed" and wid:
        plan = metadata.get("plan", "free")
        if plan in PLANS:
            db().execute("UPDATE workspaces SET plan=?,stripe_customer_id=?,stripe_subscription_id=? WHERE id=?",
                         (plan,obj.get("customer"),obj.get("subscription"),wid))
            db().commit()
    elif typ == "customer.subscription.updated":
        wid = metadata.get("workspace_id")
        plan = metadata.get("plan", "free")
        if wid and plan in PLANS:
            db().execute("UPDATE workspaces SET plan=?,stripe_customer_id=?,stripe_subscription_id=? WHERE id=?",
                         (plan,obj.get("customer"),obj.get("id"),wid))
            db().commit()
    elif typ == "customer.subscription.deleted":
        wid = metadata.get("workspace_id")
        if wid:
            db().execute("UPDATE workspaces SET plan='free',stripe_subscription_id=NULL WHERE id=?",(wid,))
            db().commit()
    return "ok", 200

@app.route("/billing/success")
@login_required
@workspace_required
def billing_success():
    flash("Checkout finished. Your plan will activate after Stripe confirms the payment.")
    return redirect(url_for("billing"))

with app.app_context():
    init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
