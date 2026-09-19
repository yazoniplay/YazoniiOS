import os
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, g, redirect, render_template_string, request, session, url_for, flash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
DB_PATH = os.getenv("DATABASE_PATH", "signalbox.db")

CSS = """
<style>
:root{--bg:#08090b;--panel:#101216;--panel2:#17191e;--line:#282c34;--text:#f5f5f2;--muted:#969aa3;--accent:#ff6a00}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px Inter,system-ui,sans-serif}a{color:inherit;text-decoration:none}
.shell{max-width:1120px;margin:auto;padding:0 22px}.nav{height:70px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
.logo{font-weight:900;font-size:20px}.logo span{color:var(--accent)}.navlinks{display:flex;gap:18px;align-items:center;color:var(--muted)}.navlinks a:hover{color:#fff}
.btn{display:inline-block;border:1px solid var(--line);background:var(--panel2);border-radius:9px;padding:10px 14px;cursor:pointer}.primary{background:var(--accent);border-color:var(--accent);color:#111;font-weight:800}
.hero{padding:86px 0 68px;max-width:900px}.kicker{font-size:12px;text-transform:uppercase;letter-spacing:1.5px;font-weight:800;color:#ff9a4d}
h1{font-size:clamp(44px,7vw,78px);line-height:.98;letter-spacing:-3.5px;margin:14px 0 20px}.hero p{font-size:19px;line-height:1.55;color:var(--muted);max-width:720px}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:27px}.section{padding:20px 0 70px}.head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin-bottom:18px}.head h2{margin:0;font-size:25px}
.muted{color:var(--muted)}.search{display:flex;gap:8px}.search input{background:#0c0d10;border:1px solid var(--line);color:#fff;border-radius:9px;padding:10px 12px}
.chips{display:flex;gap:8px;overflow:auto;margin-bottom:18px}.chip{border:1px solid var(--line);border-radius:999px;padding:8px 12px;color:var(--muted);white-space:nowrap}.chip.active{color:#fff;border-color:#8d3e0b;background:#1a110b}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden;transition:.15s}.card:hover{transform:translateY(-2px);border-color:#454a55}
.visual{height:150px;background:linear-gradient(135deg,#20232a,#0d0f12);padding:17px;display:flex;align-items:end;font-weight:900;font-size:23px}.body{padding:16px}.tag{font-size:11px;color:#ff9a4d;text-transform:uppercase;letter-spacing:1px;font-weight:800}.body h3{margin:7px 0;font-size:19px}.body p{color:var(--muted);line-height:1.45;margin:0 0 15px}.row{display:flex;justify-content:space-between;align-items:center}.price{font-weight:900;font-size:18px}
.avatar{width:29px;height:29px;border-radius:50%;background:#252933;display:inline-grid;place-items:center;font-weight:800}.seller{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:24px}.form{max-width:600px;margin:60px auto}.field{margin:15px 0}.field label{display:block;color:var(--muted);font-size:13px;margin-bottom:7px}.field input,.field textarea,.field select{width:100%;padding:11px;background:#0b0c0f;border:1px solid var(--line);color:#fff;border-radius:9px;font:inherit}.field textarea{min-height:130px}.flash{margin:15px 0;padding:11px 13px;border:1px solid #513019;background:#19120d;border-radius:9px;color:#ffd8bd}
.feature{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:15px}.feature .panel{padding:20px}.feature b{display:block;margin-bottom:6px}
.product{padding:55px 0}.productgrid{display:grid;grid-template-columns:1.2fr .8fr;gap:25px}.productvisual{min-height:410px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(135deg,#20232a,#0d0f12);padding:30px;display:flex;flex-direction:column;justify-content:end}.productvisual h1{font-size:55px;margin:8px 0}.buy{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:24px;height:max-content;position:sticky;top:18px}.bigprice{font-size:38px;font-weight:900;margin:8px 0 22px}.buy .btn{display:block;text-align:center}.note{color:var(--muted);font-size:13px;line-height:1.5;margin-top:13px}
.dash{padding:45px 0}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}.stat{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:18px}.stat b{display:block;font-size:28px;margin-top:5px}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:12px;border-bottom:1px solid var(--line)}
.footer{border-top:1px solid var(--line);padding:28px 0;color:var(--muted);font-size:13px}
@media(max-width:760px){.grid{grid-template-columns:1fr 1fr}.productgrid{grid-template-columns:1fr}.buy{position:static}.feature,.stats{grid-template-columns:1fr}.navlinks a:not(.btn){display:none}}
@media(max-width:520px){.grid{grid-template-columns:1fr}.hero{padding-top:55px}h1{letter-spacing:-2px}.search input{width:130px}}
</style>
"""

BASE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Signalbox</title>""" + CSS + """</head><body><div class="shell">
<nav class="nav"><a class="logo" href="{{url_for('home')}}">SIGNAL<span>.</span></a><div class="navlinks"><a href="{{url_for('home')}}">Discover</a>{%if session.get('user_id')%}<a href="{{url_for('submit')}}">Submit</a><a href="{{url_for('dashboard')}}">My signals</a><a href="{{url_for('logout')}}">Log out</a>{%else%}<a href="{{url_for('login')}}">Log in</a><a class="btn" href="{{url_for('signup')}}">Create account</a>{%endif%}</div></nav>
{%for m in get_flashed_messages()%}<div class="flash">{{m}}</div>{%endfor%}{{body|safe}}
<footer class="footer">SIGNAL · Find what people actually need.</footer></div></body></html>"""

TOPICS=["Apps","Gaming","Creators","Shopping","Education","Business","Other"]

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
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,handle TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS signals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,title TEXT NOT NULL,
        problem TEXT NOT NULL,category TEXT NOT NULL,urgency INTEGER DEFAULT 3,
        created_at TEXT NOT NULL,active INTEGER DEFAULT 1)""")
    c.commit(); c.close()

def current_user():
    uid=session.get("user_id")
    return db().execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone() if uid else None

def auth(fn):
    @wraps(fn)
    def wrapped(*a,**kw):
        if not current_user(): return redirect(url_for("login"))
        return fn(*a,**kw)
    return wrapped

@app.route("/")
def home():
    q=request.args.get("q","").strip(); topic=request.args.get("topic","")
    sql="SELECT s.*,u.handle FROM signals s JOIN users u ON u.id=s.user_id WHERE s.active=1"; params=[]
    if q:
        x=f"%{q}%"; sql+=" AND (s.title LIKE ? OR s.problem LIKE ? OR u.handle LIKE ?)"; params += [x,x,x]
    if topic in TOPICS: sql+=" AND s.category=?"; params.append(topic)
    sql+=" ORDER BY s.id DESC"
    signals=db().execute(sql,params).fetchall()
    body=render_template_string("""<section class="hero"><div class="kicker">Demand intelligence</div><h1>See what people actually need.</h1><p>SIGNAL turns real problems into a public demand map. Post a problem, find people with the same need, and discover ideas worth building.</p><div class="actions"><a class="btn primary" href="#discover">Explore demand</a><a class="btn" href="{{url_for('signup')}}">Post a problem</a></div><div class="feature"><div class="panel"><b>Real problems</b><span class="muted">Short, concrete requests instead of trend-chasing.</span></div><div class="panel"><b>Find your people</b><span class="muted">See who has the same problem.</span></div><div class="panel"><b>Build from demand</b><span class="muted">Use signals to choose what to make next.</span></div></div></section>
<section class="section" id="discover"><div class="head"><div><h2>Latest signals</h2><span class="muted">{{signals|length}} public signals</span></div><form class="search"><input name="q" value="{{q}}" placeholder="Search a problem..."><button class="btn">Search</button></form></div>
<div class="chips"><a class="chip {{'active' if not topic else ''}}" href="{{url_for('home')}}">All</a>{%for t in topics%}<a class="chip {{'active' if topic==t else ''}}" href="{{url_for('home',topic=t)}}">{{t}}</a>{%endfor%}</div>
{%if signals%}<div class="grid">{%for s in signals%}<a class="card" href="{{url_for('signal',signal_id=s.id)}}"><div class="visual">{{s.title[:26]}}</div><div class="body"><div class="tag">{{s.category}}</div><h3>{{s.title}}</h3><p>{{s.problem[:115]}}{{'...' if s.problem|length>115 else ''}}</p><div class="row"><div class="seller"><span class="avatar">{{s.handle[0]|upper}}</span>@{{s.handle}}</div><span class="muted">Need {{s.urgency}}/5</span></div></div></a>{%endfor%}</div>{%else%}<div class="panel" style="text-align:center;padding:55px"><h2>No signals yet.</h2><p class="muted">Be the first person to post a real problem.</p><a class="btn primary" href="{{url_for('signup')}}">Post one</a></div>{%endif%}</section>""",signals=signals,topics=TOPICS,q=q,topic=topic)
    return render_template_string(BASE,title="Discover",body=body)

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); password=request.form.get("password",""); handle=request.form.get("handle","").strip().lower().replace(" ","")
        if len(name)<2 or "@" not in email or len(password)<8 or len(handle)<3: flash("Enter a valid name, email, handle and 8+ character password.")
        elif db().execute("SELECT id FROM users WHERE email=? OR handle=?",(email,handle)).fetchone(): flash("That email or handle is already taken.")
        else:
            from werkzeug.security import generate_password_hash
            c=db(); c.execute("INSERT INTO users(name,email,password_hash,handle,created_at) VALUES(?,?,?,?,?)",(name,email,generate_password_hash(password),handle,datetime.utcnow().isoformat())); uid=c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.commit()
            session.clear(); session["user_id"]=uid; return redirect(url_for("dashboard"))
    body=render_template_string("""<div class="form"><div class="panel"><div class="kicker">Join SIGNAL</div><h1 style="font-size:43px;letter-spacing:-2px">Post what you need.</h1><p class="muted">Turn a frustration into a public demand signal.</p><form method="post"><div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Handle</label><input name="handle" placeholder="yazonii" required></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" minlength="8" required></div><button class="btn primary">Create account</button></form></div></div>""")
    return render_template_string(BASE,title="Create account",body=body)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        from werkzeug.security import check_password_hash
        u=db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").strip().lower(),)).fetchone()
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session["user_id"]=u["id"]; return redirect(url_for("dashboard"))
        flash("Wrong email or password.")
    body=render_template_string("""<div class="form"><div class="panel"><div class="kicker">Welcome back</div><h1 style="font-size:43px;letter-spacing:-2px">Log in.</h1><form method="post"><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" required></div><button class="btn primary">Log in</button></form><p class="muted">Need an account? <a href="{{url_for('signup')}}" style="color:#fff">Create one</a></p></div></div>""")
    return render_template_string(BASE,title="Log in",body=body)

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/submit",methods=["GET","POST"])
@auth
def submit():
    if request.method=="POST":
        title=request.form.get("title","").strip(); problem=request.form.get("problem","").strip(); category=request.form.get("category","Other"); urgency=int(request.form.get("urgency","3"))
        if not title or len(problem)<15 or category not in TOPICS or urgency not in range(1,6): flash("Add a clear title, a useful description, category and urgency.")
        else:
            db().execute("INSERT INTO signals(user_id,title,problem,category,urgency,created_at) VALUES(?,?,?,?,?,?)",(current_user()["id"],title,problem,category,urgency,datetime.utcnow().isoformat())); db().commit(); flash("Signal published."); return redirect(url_for("dashboard"))
    body=render_template_string("""<div class="form"><div class="panel"><div class="kicker">New demand signal</div><h1 style="font-size:43px;letter-spacing:-2px">What problem keeps annoying you?</h1><p class="muted">Be specific. A strong signal describes the problem, who it affects and what you wish existed.</p><form method="post"><div class="field"><label>Short title</label><input name="title" placeholder="I need a simple way to..." required></div><div class="field"><label>The problem</label><textarea name="problem" placeholder="What are you trying to do? What fails today? What would a good solution look like?" required></textarea></div><div class="field"><label>Category</label><select name="category">{%for t in topics%}<option>{{t}}</option>{%endfor%}</select></div><div class="field"><label>How badly do you need it? (1–5)</label><input name="urgency" type="number" min="1" max="5" value="4" required></div><button class="btn primary">Publish signal</button></form></div></div>""",topics=TOPICS)
    return render_template_string(BASE,title="Post a problem",body=body)

@app.route("/signal/<int:signal_id>")
def signal(signal_id):
    s=db().execute("SELECT s.*,u.handle,u.name FROM signals s JOIN users u ON u.id=s.user_id WHERE s.id=? AND s.active=1",(signal_id,)).fetchone()
    if not s:return "Signal not found",404
    related=db().execute("SELECT * FROM signals WHERE id!=? AND category=? AND active=1 ORDER BY id DESC LIMIT 3",(signal_id,s["category"])).fetchall()
    body=render_template_string("""<section class="product"><div class="productgrid"><div class="panel" style="min-height:350px"><div class="kicker">{{s.category}}</div><h1 style="font-size:52px">{{s.title}}</h1><p class="muted" style="font-size:18px;line-height:1.65;white-space:pre-line">{{s.problem}}</p><div class="seller"><span class="avatar">{{s.handle[0]|upper}}</span>@{{s.handle}} · Need {{s.urgency}}/5</div></div><aside class="buy"><div class="muted">Demand signal</div><div class="bigprice">{{s.urgency}}/5</div><div class="note">This is a public request. Future versions can let people follow the signal, pledge interest, or connect builders with people who need the same thing.</div></aside></div><div style="margin-top:25px"><h2>More in {{s.category}}</h2><div class="grid">{%for r in related%}<a class="card" href="{{url_for('signal',signal_id=r.id)}}"><div class="body"><div class="tag">{{r.category}}</div><h3>{{r.title}}</h3><p>{{r.problem[:90]}}</p></div></a>{%endfor%}</div></div></section>""",s=s,related=related)
    return render_template_string(BASE,title=s["title"],body=body)

@app.route("/dashboard")
@auth
def dashboard():
    u=current_user(); signals=db().execute("SELECT * FROM signals WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    body=render_template_string("""<section class="dash"><div class="head"><div><div class="kicker">Your demand</div><h1 style="font-size:45px;margin:6px 0">@{{u.handle}}</h1><p class="muted">Signals you've published.</p></div><a class="btn primary" href="{{url_for('submit')}}">+ Post signal</a></div><div class="stats"><div class="stat"><span class="muted">Signals</span><b>{{signals|length}}</b></div><div class="stat"><span class="muted">Highest urgency</span><b>{{signals|map(attribute='urgency')|max if signals else 0}}/5</b></div><div class="stat"><span class="muted">Status</span><b>Public</b></div></div><div class="panel">{%if signals%}<table class="table"><tr><th>Signal</th><th>Topic</th><th>Urgency</th><th>Date</th></tr>{%for s in signals%}<tr><td><a href="{{url_for('signal',signal_id=s.id)}}"><b>{{s.title}}</b></a></td><td>{{s.category}}</td><td>{{s.urgency}}/5</td><td>{{s.created_at[:10]}}</td></tr>{%endfor%}</table>{%else%}<p class="muted">You haven't published a signal yet.</p>{%endif%}</div></section>""",u=u,signals=signals)
    return render_template_string(BASE,title="My signals",body=body)

with app.app_context(): init_db()

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
