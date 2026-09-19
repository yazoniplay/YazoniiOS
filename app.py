import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, g, redirect, render_template_string, request, session, url_for, flash

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")
DB_PATH = os.getenv("DATABASE_PATH", "marketforge.db")

CATEGORIES = ["Gaming", "Design", "Code", "Education", "Business", "Templates", "Other"]

CSS = """
<style>
:root{--bg:#090a0c;--panel:#111317;--panel2:#17191e;--line:#292c33;--text:#f4f5f7;--muted:#969ba6;--accent:#ff6a00;--accent2:#ff9a4d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:inherit;text-decoration:none}.shell{max-width:1180px;margin:auto;padding:0 22px}
.nav{height:72px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line)}
.logo{font-size:21px;font-weight:900;letter-spacing:-.7px}.logo i{font-style:normal;color:var(--accent)}
.navlinks{display:flex;gap:18px;color:var(--muted);align-items:center}.navlinks a:hover{color:#fff}
.btn{display:inline-block;border:1px solid var(--line);background:var(--panel2);padding:10px 14px;border-radius:9px;color:#fff;cursor:pointer}.btn:hover{border-color:#444}.btn.primary{background:var(--accent);border-color:var(--accent);color:#111;font-weight:800}
.hero{padding:78px 0 55px;max-width:850px}.eyebrow{color:var(--accent2);font-weight:800;text-transform:uppercase;font-size:12px;letter-spacing:1.4px}
h1{font-size:clamp(42px,7vw,76px);line-height:.98;letter-spacing:-3px;margin:14px 0}.hero p{font-size:19px;color:var(--muted);max-width:690px;line-height:1.55}
.actions{display:flex;gap:10px;margin-top:26px;flex-wrap:wrap}
.section{padding:30px 0 65px}.sectionhead{display:flex;justify-content:space-between;align-items:end;gap:15px;margin-bottom:18px}.sectionhead h2{margin:0;font-size:25px}.muted{color:var(--muted)}
.filters{display:flex;gap:8px;overflow:auto;padding-bottom:12px}.filter{white-space:nowrap;padding:8px 12px;border:1px solid var(--line);border-radius:999px;color:var(--muted)}.filter.active{color:#fff;border-color:var(--accent);background:#1c120c}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}.thumb{height:155px;background:linear-gradient(135deg,#1b1d22,#0e1013);display:flex;align-items:end;padding:16px;font-weight:900;font-size:24px}.cardbody{padding:16px}.category{font-size:11px;color:var(--accent2);text-transform:uppercase;font-weight:800;letter-spacing:.9px}.card h3{margin:7px 0;font-size:19px}.card p{color:var(--muted);line-height:1.45;margin:0 0 14px}.meta{display:flex;justify-content:space-between;align-items:center}.price{font-size:18px;font-weight:900}
.sellerbar{display:flex;align-items:center;gap:9px;color:var(--muted);font-size:13px}.avatar{width:28px;height:28px;border-radius:50%;background:#242832;display:grid;place-items:center;color:#fff;font-weight:800}
.formwrap{max-width:600px;margin:55px auto}.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:25px}.field{margin:15px 0}.field label{display:block;color:var(--muted);font-size:13px;margin-bottom:7px}.field input,.field textarea,.field select{width:100%;background:#0b0c0f;color:#fff;border:1px solid var(--line);border-radius:9px;padding:11px;font:inherit}.field textarea{min-height:140px;resize:vertical}.flash{margin:15px 0;padding:11px 13px;background:#17120e;border:1px solid #4c2b14;border-radius:9px;color:#ffd7bb}
.product{padding:55px 0}.productgrid{display:grid;grid-template-columns:1.15fr .85fr;gap:28px}.producthero{min-height:400px;background:linear-gradient(135deg,#1b1d22,#0e1013);border:1px solid var(--line);border-radius:18px;padding:28px;display:flex;flex-direction:column;justify-content:end}.producthero h1{font-size:52px;letter-spacing:-2px;margin:8px 0}.buybox{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:25px;height:max-content;position:sticky;top:20px}.bigprice{font-size:38px;font-weight:900;margin:8px 0 22px}.buybox .btn{width:100%;text-align:center}.notice{margin-top:15px;color:var(--muted);font-size:13px;line-height:1.5}
.dashboard{padding:42px 0}.dashhead{display:flex;justify-content:space-between;align-items:center;gap:15px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:22px 0}.stat{padding:18px;background:var(--panel);border:1px solid var(--line);border-radius:13px}.stat b{display:block;font-size:27px;margin-top:6px}.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:13px;border-bottom:1px solid var(--line)}.table th{font-size:11px;color:var(--muted);text-transform:uppercase}
.footer{border-top:1px solid var(--line);padding:28px 0;color:var(--muted);font-size:13px}
@media(max-width:800px){.grid{grid-template-columns:1fr 1fr}.productgrid{grid-template-columns:1fr}.buybox{position:static}.navlinks a:not(.btn){display:none}}
@media(max-width:540px){.grid,.stats{grid-template-columns:1fr}.hero{padding-top:55px}h1{letter-spacing:-2px}.producthero h1{font-size:38px}}
</style>
"""

BASE = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · Forge</title>""" + CSS + """</head><body><div class="shell">
<nav class="nav"><a class="logo" href="{{url_for('home')}}">FORGE<i>.</i></a><div class="navlinks"><a href="{{url_for('home')}}">Discover</a>{% if session.get('user_id') %}<a href="{{url_for('sell')}}">Sell</a><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('logout')}}">Log out</a>{% else %}<a href="{{url_for('login')}}">Log in</a><a class="btn" href="{{url_for('signup')}}">Start selling</a>{% endif %}</div></nav>
{% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}{{body|safe}}
<footer class="footer">FORGE · A marketplace for useful things made by creators.</footer></div></body></html>"""

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn: conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL, handle TEXT UNIQUE NOT NULL, bio TEXT DEFAULT '',
        created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER NOT NULL, title TEXT NOT NULL,
        description TEXT NOT NULL, price REAL NOT NULL, category TEXT NOT NULL,
        accent TEXT DEFAULT 'orange', created_at TEXT NOT NULL, active INTEGER DEFAULT 1)""")
    conn.commit(); conn.close()

def user():
    uid=session.get("user_id")
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone() if uid else None

def auth(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not user():
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return wrapped

@app.route("/")
def home():
    q=request.args.get("q","").strip()
    category=request.args.get("category","")
    sql="""SELECT p.*,u.name,u.handle FROM products p JOIN users u ON u.id=p.seller_id WHERE p.active=1"""
    params=[]
    if q:
        sql += " AND (p.title LIKE ? OR p.description LIKE ? OR u.handle LIKE ?)"
        x=f"%{q}%"; params += [x,x,x]
    if category in CATEGORIES:
        sql += " AND p.category=?"; params.append(category)
    sql += " ORDER BY p.id DESC"
    products=db().execute(sql,params).fetchall()
    body=render_template_string("""<section class="hero"><div class="eyebrow">Creator commerce</div><h1>Find things worth buying.</h1><p>FORGE is a marketplace for digital products, tools, templates and knowledge made by independent creators.</p><div class="actions"><a class="btn primary" href="#discover">Explore products</a><a class="btn" href="{{url_for('signup')}}">Build a storefront</a></div></section>
<section class="section" id="discover"><div class="sectionhead"><div><h2>Discover</h2><span class="muted">{{products|length}} products</span></div><form><input name="q" value="{{q}}" placeholder="Search products..." style="background:#0b0c0f;color:white;border:1px solid #292c33;border-radius:9px;padding:10px 12px"></form></div>
<div class="filters"><a class="filter {{'active' if not category else ''}}" href="{{url_for('home')}}">All</a>{%for c in categories%}<a class="filter {{'active' if category==c else ''}}" href="{{url_for('home',category=c)}}">{{c}}</a>{%endfor%}</div>
{%if products%}<div class="grid">{%for p in products%}<a class="card" href="{{url_for('product',product_id=p.id)}}"><div class="thumb">{{p.title[:22]}}</div><div class="cardbody"><div class="category">{{p.category}}</div><h3>{{p.title}}</h3><p>{{p.description[:100]}}{{'...' if p.description|length>100 else ''}}</p><div class="meta"><div class="sellerbar"><span class="avatar">{{p.handle[0]|upper}}</span>@{{p.handle}}</div><span class="price">€{{"%.2f"|format(p.price)}}</span></div></div></a>{%endfor%}</div>{%else%}<div class="panel" style="text-align:center;padding:55px"><h2>No products yet.</h2><p class="muted">Be the first creator to publish something.</p><a class="btn primary" href="{{url_for('signup')}}">Start selling</a></div>{%endif%}</section>""",products=products,categories=CATEGORIES,q=q,category=category)
    return render_template_string(BASE,title="Discover",body=body)

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower()
        password=request.form.get("password",""); handle=request.form.get("handle","").strip().lower().replace(" ","")
        if len(name)<2 or "@" not in email or len(password)<8 or len(handle)<3:
            flash("Use a name, valid email, handle, and an 8+ character password.")
        elif db().execute("SELECT id FROM users WHERE email=? OR handle=?", (email,handle)).fetchone():
            flash("That email or handle is already taken.")
        else:
            from werkzeug.security import generate_password_hash
            cur=db(); cur.execute("INSERT INTO users(name,email,password_hash,handle,created_at) VALUES(?,?,?,?,?)",(name,email,generate_password_hash(password),handle,datetime.utcnow().isoformat()))
            uid=cur.execute("SELECT last_insert_rowid()").fetchone()[0]; cur.commit()
            session.clear(); session["user_id"]=uid; return redirect(url_for("dashboard"))
    body=render_template_string("""<div class="formwrap"><div class="panel"><div class="eyebrow">Creator account</div><h1 style="font-size:42px;letter-spacing:-2px">Build your storefront.</h1><p class="muted">Publish products and give your audience one place to buy.</p><form method="post"><div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Handle</label><input name="handle" placeholder="yazonii" required></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" minlength="8" required></div><button class="btn primary">Create storefront</button></form><p class="muted">Already registered? <a href="{{url_for('login')}}" style="color:#fff">Log in</a></p></div></div>""")
    return render_template_string(BASE,title="Create account",body=body)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        from werkzeug.security import check_password_hash
        u=db().execute("SELECT * FROM users WHERE email=?", (request.form.get("email","").strip().lower(),)).fetchone()
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):
            session.clear(); session["user_id"]=u["id"]; return redirect(url_for("dashboard"))
        flash("Wrong email or password.")
    body=render_template_string("""<div class="formwrap"><div class="panel"><div class="eyebrow">Welcome back</div><h1 style="font-size:42px;letter-spacing:-2px">Log in.</h1><form method="post"><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" required></div><button class="btn primary">Log in</button></form><p class="muted">No account? <a href="{{url_for('signup')}}" style="color:#fff">Start selling</a></p></div></div>""")
    return render_template_string(BASE,title="Log in",body=body)

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/sell",methods=["GET","POST"])
@auth
def sell():
    if request.method=="POST":
        title=request.form.get("title","").strip(); description=request.form.get("description","").strip()
        try: price=float(request.form.get("price","0"))
        except: price=-1
        category=request.form.get("category","Other")
        if not title or len(description)<10 or price<0 or category not in CATEGORIES:
            flash("Add a title, a useful description, a valid price, and a category.")
        else:
            db().execute("INSERT INTO products(seller_id,title,description,price,category,created_at) VALUES(?,?,?,?,?,?)",(user()["id"],title,description,price,category,datetime.utcnow().isoformat())); db().commit()
            flash("Product published."); return redirect(url_for("dashboard"))
    body=render_template_string("""<div class="formwrap"><div class="panel"><div class="eyebrow">New product</div><h1 style="font-size:42px;letter-spacing:-2px">Publish something useful.</h1><p class="muted">Start with the offer. Payments and delivery can be connected once the marketplace is validated.</p><form method="post"><div class="field"><label>Product name</label><input name="title" placeholder="PvP Practice Pack" required></div><div class="field"><label>Description</label><textarea name="description" placeholder="What does the buyer get? What problem does it solve?" required></textarea></div><div class="field"><label>Price (€)</label><input name="price" type="number" min="0" step="0.01" required></div><div class="field"><label>Category</label><select name="category">{%for c in categories%}<option>{{c}}</option>{%endfor%}</select></div><button class="btn primary">Publish product</button></form></div></div>""",categories=CATEGORIES)
    return render_template_string(BASE,title="Sell",body=body)

@app.route("/product/<int:product_id>")
def product(product_id):
    p=db().execute("SELECT p.*,u.name,u.handle,u.bio FROM products p JOIN users u ON u.id=p.seller_id WHERE p.id=? AND p.active=1",(product_id,)).fetchone()
    if not p:return "Product not found",404
    body=render_template_string("""<section class="product"><div class="productgrid"><div class="producthero"><div class="category">{{p.category}}</div><h1>{{p.title}}</h1><div class="sellerbar"><span class="avatar">{{p.handle[0]|upper}}</span>by @{{p.handle}}</div></div><aside class="buybox"><div class="muted">One-time purchase</div><div class="bigprice">€{{"%.2f"|format(p.price)}}</div><a class="btn primary" href="{{url_for('checkout_demo',product_id=p.id)}}">Get this product</a><div class="notice">Demo checkout for the MVP. No real payment is processed yet.</div></aside></div><div style="max-width:760px;margin-top:28px"><div class="panel"><div class="eyebrow">About this product</div><h2>{{p.title}}</h2><p class="muted" style="white-space:pre-line;line-height:1.7">{{p.description}}</p><hr style="border:0;border-top:1px solid #292c33;margin:25px 0"><div class="sellerbar"><span class="avatar">{{p.handle[0]|upper}}</span><div><b>@{{p.handle}}</b><br><span>{{p.bio or 'Independent creator'}}</span></div></div></div></div></section>""",p=p)
    return render_template_string(BASE,title=p["title"],body=body)

@app.route("/checkout-demo/<int:product_id>")
def checkout_demo(product_id):
    p=db().execute("SELECT * FROM products WHERE id=? AND active=1",(product_id,)).fetchone()
    if not p:return "Product not found",404
    flash("Demo order created. Real checkout + creator payouts are the next integration.")
    return redirect(url_for("product",product_id=product_id))

@app.route("/dashboard")
@auth
def dashboard():
    u=user(); products=db().execute("SELECT * FROM products WHERE seller_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    revenue=sum(float(p["price"]) for p in products)
    body=render_template_string("""<section class="dashboard"><div class="dashhead"><div><div class="eyebrow">Creator dashboard</div><h1 style="font-size:44px;letter-spacing:-2px;margin:7px 0">@{{u.handle}}</h1><p class="muted">Your storefront is live.</p></div><a class="btn primary" href="{{url_for('sell')}}">+ New product</a></div><div class="stats"><div class="stat"><span class="muted">Published products</span><b>{{products|length}}</b></div><div class="stat"><span class="muted">Catalog value</span><b>€{{"%.2f"|format(revenue)}}</b></div><div class="stat"><span class="muted">Storefront</span><b>Live</b></div></div><div class="panel"><div class="sectionhead"><h2>Your products</h2><a class="btn" href="{{url_for('home',q=u.handle)}}">View marketplace</a></div>{%if products%}<table class="table"><tr><th>Product</th><th>Category</th><th>Price</th><th>Published</th></tr>{%for p in products%}<tr><td><a href="{{url_for('product',product_id=p.id)}}"><b>{{p.title}}</b></a></td><td>{{p.category}}</td><td>€{{"%.2f"|format(p.price)}}</td><td>{{p.created_at[:10]}}</td></tr>{%endfor%}</table>{%else%}<p class="muted">No products yet. Publish the first one.</p>{%endif%}</div></section>""",u=u,products=products,revenue=revenue)
    return render_template_string(BASE,title="Dashboard",body=body)

with app.app_context():
    init_db()

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
