import os, sqlite3, json
from datetime import datetime
from functools import wraps
from flask import Flask,g,redirect,render_template_string,request,session,url_for,flash

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY","dev-only-change-me")
DB_PATH=os.getenv("DATABASE_PATH","agentready.db")

CSS="""<style>
:root{--bg:#08090b;--p:#111318;--p2:#171a20;--l:#292d35;--t:#f5f5f2;--m:#9297a1;--a:#ff6a00}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:15px Inter,system-ui,sans-serif}a{color:inherit;text-decoration:none}
.shell{max-width:1140px;margin:auto;padding:0 22px}.nav{height:70px;border-bottom:1px solid var(--l);display:flex;align-items:center;justify-content:space-between}.logo{font-weight:950;font-size:20px}.logo i{color:var(--a);font-style:normal}.navlinks{display:flex;gap:18px;align-items:center;color:var(--m)}.navlinks a:hover{color:#fff}
.btn{border:1px solid var(--l);background:var(--p2);color:#fff;border-radius:9px;padding:10px 14px;display:inline-block;cursor:pointer}.primary{background:var(--a);border-color:var(--a);color:#111;font-weight:850}
.hero{padding:85px 0 55px;max-width:920px}.k{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;font-weight:850;color:#ff9a4d}h1{font-size:clamp(44px,7vw,78px);line-height:.98;letter-spacing:-3.5px;margin:14px 0 20px}.hero p{font-size:19px;line-height:1.55;color:var(--m);max-width:760px}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:25px}
.section{padding:22px 0 70px}.head{display:flex;justify-content:space-between;align-items:end;gap:15px;margin-bottom:18px}.head h2{margin:0}.muted{color:var(--m)}
.panel{background:var(--p);border:1px solid var(--l);border-radius:15px;padding:22px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.card{background:var(--p);border:1px solid var(--l);border-radius:14px;padding:17px}.card:hover{border-color:#4b505b}.tag{font-size:11px;color:#ff9a4d;text-transform:uppercase;font-weight:850;letter-spacing:1px}.card h3{margin:8px 0}.card p{color:var(--m);line-height:1.45;margin:0 0 13px}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px}.score{font-weight:900}.pill{padding:5px 8px;border-radius:999px;background:#1b130d;color:#ffb078;font-size:12px}.form{max-width:700px;margin:55px auto}.field{margin:15px 0}.field label{display:block;color:var(--m);font-size:13px;margin-bottom:7px}.field input,.field textarea,.field select{width:100%;background:#0b0c0f;color:#fff;border:1px solid var(--l);border-radius:9px;padding:11px;font:inherit}.field textarea{min-height:130px}.flash{margin:15px 0;padding:11px;border:1px solid #513019;background:#19120d;border-radius:9px;color:#ffd9c0}
pre{white-space:pre-wrap;background:#090a0c;border:1px solid var(--l);border-radius:10px;padding:15px;overflow:auto;color:#dfe2e8}.grid2{display:grid;grid-template-columns:1.15fr .85fr;gap:18px}.statgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.stat{background:var(--p);border:1px solid var(--l);border-radius:13px;padding:18px}.stat b{font-size:27px;display:block;margin-top:6px}
.table{width:100%;border-collapse:collapse}.table th,.table td{text-align:left;padding:12px;border-bottom:1px solid var(--l)}.footer{border-top:1px solid var(--l);padding:28px 0;color:var(--m);font-size:13px}
@media(max-width:760px){.cards,.statgrid{grid-template-columns:1fr 1fr}.grid2{grid-template-columns:1fr}.navlinks a:not(.btn){display:none}}@media(max-width:520px){.cards,.statgrid{grid-template-columns:1fr}h1{letter-spacing:-2px}}
</style>"""
BASE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · AGENTREADY</title>"""+CSS+"""</head><body><div class="shell"><nav class="nav"><a class="logo" href="{{url_for('home')}}">AGENT<span class="logo">READY<i>.</i></span></a><div class="navlinks"><a href="{{url_for('home')}}">Catalog</a>{%if session.get('user_id')%}<a href="{{url_for('products')}}">Products</a><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('logout')}}">Log out</a>{%else%}<a href="{{url_for('login')}}">Log in</a><a class="btn" href="{{url_for('signup')}}">Get started</a>{%endif%}</div></nav>{%for m in get_flashed_messages()%}<div class="flash">{{m}}</div>{%endfor%}{{body|safe}}<footer class="footer">AGENTREADY · Make your catalog ready for the next shopping interface.</footer></div></body></html>"""

def db():
    if "db" not in g:g.db=sqlite3.connect(DB_PATH);g.db.row_factory=sqlite3.Row
    return g.db
@app.teardown_appcontext
def close(exc):
    c=g.pop("db",None)
    if c:c.close()
def init():
    c=sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,description TEXT NOT NULL,
      price TEXT NOT NULL,currency TEXT NOT NULL,availability TEXT NOT NULL,shipping TEXT NOT NULL,
      url TEXT NOT NULL,attributes TEXT NOT NULL,created_at TEXT NOT NULL)""")
    c.commit();c.close()
def me():
    uid=session.get("user_id");return db().execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone() if uid else None
def auth(fn):
    @wraps(fn)
    def w(*a,**kw):
        if not me():return redirect(url_for("login"))
        return fn(*a,**kw)
    return w
def normalize(p):
    attrs={}
    try: attrs=json.loads(p["attributes"] or "{}")
    except: pass
    return {**dict(p),"attributes":attrs}
def agent_json(p):
    p=normalize(p)
    return json.dumps({"name":p["name"],"description":p["description"],"price":{"amount":p["price"],"currency":p["currency"]},"availability":p["availability"],"shipping":p["shipping"],"url":p["url"],"attributes":p["attributes"]},indent=2)

@app.route("/")
def home():
    ps=db().execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    body=render_template_string("""<section class="hero"><div class="k">Agentic commerce infrastructure</div><h1>Your products need to be readable by machines.</h1><p>AGENTREADY turns a normal product catalog into structured, agent-ready product data — the foundation for being discovered accurately as AI shopping becomes a real channel.</p><div class="actions"><a class="btn primary" href="{{url_for('signup')}}">Make a catalog agent-ready</a><a class="btn" href="#how">See the output</a></div><div class="statgrid" style="margin-top:30px"><div class="stat"><span class="muted">One catalog</span><b>→ many agents</b></div><div class="stat"><span class="muted">Structured data</span><b>Live-ready</b></div><div class="stat"><span class="muted">Built for</span><b>AI discovery</b></div></div></section>
<section class="section" id="how"><div class="head"><div><h2>What it produces</h2><span class="muted">A machine-readable catalog layer</span></div></div><div class="grid2"><div class="panel"><div class="k">Example product record</div><pre>{{sample}}</pre></div><div class="panel"><h2>Why this exists</h2><p class="muted" style="line-height:1.7">AI shopping systems need accurate names, prices, availability, shipping and attributes. The industry is moving toward agentic commerce standards, while merchants face multiple channels and formats.</p><p class="muted" style="line-height:1.7">The MVP starts with the narrow infrastructure layer: normalize the merchant's catalog once, then expose it cleanly to future AI commerce channels.</p></div></div></section>
<section class="section"><div class="head"><h2>Demo catalog</h2><span class="muted">{{ps|length}} products</span></div>{%if ps%}<div class="cards">{%for p in ps%}<a class="card" href="{{url_for('product',pid=p.id)}}"><div class="tag">agent-ready</div><h3>{{p.name}}</h3><p>{{p.description[:100]}}</p><div class="row"><span>{{p.price}} {{p.currency}}</span><span class="pill">{{p.availability}}</span></div></a>{%endfor%}</div>{%else%}<div class="panel"><h3>No products yet.</h3><p class="muted">Create the first agent-ready product catalog.</p></div>{%endif%}</section>""",ps=ps,sample='{"name":"Example Running Shoe","price":{"amount":"79.90","currency":"EUR"},"availability":"in_stock","shipping":"2-4 days","attributes":{"color":"black","size":"42"}}')
    return render_template_string(BASE,title="Home",body=body)

@app.route("/signup",methods=["GET","POST"])
def signup():
    if request.method=="POST":
        name=request.form.get("name","").strip();email=request.form.get("email","").strip().lower();pw=request.form.get("password","")
        if len(name)<2 or "@" not in email or len(pw)<8:flash("Enter a valid name, email and 8+ character password.")
        elif db().execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():flash("That email is already registered.")
        else:
            from werkzeug.security import generate_password_hash
            c=db();c.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)",(name,email,generate_password_hash(pw),datetime.utcnow().isoformat()));uid=c.execute("SELECT last_insert_rowid()").fetchone()[0];c.commit();session["user_id"]=uid;return redirect(url_for("products"))
    body=render_template_string("""<div class="form"><div class="panel"><div class="k">Merchant onboarding</div><h1 style="font-size:44px">Connect your catalog.</h1><p class="muted">Start with structured product data. No storefront rebuild required.</p><form method="post"><div class="field"><label>Name</label><input name="name" required></div><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" minlength="8" required></div><button class="btn primary">Create account</button></form></div></div>""")
    return render_template_string(BASE,title="Get started",body=body)

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        from werkzeug.security import check_password_hash
        u=db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").strip().lower(),)).fetchone()
        if u and check_password_hash(u["password_hash"],request.form.get("password","")):session["user_id"]=u["id"];return redirect(url_for("products"))
        flash("Wrong email or password.")
    body=render_template_string("""<div class="form"><div class="panel"><div class="k">Welcome back</div><h1 style="font-size:44px">Log in.</h1><form method="post"><div class="field"><label>Email</label><input name="email" type="email" required></div><div class="field"><label>Password</label><input name="password" type="password" required></div><button class="btn primary">Log in</button></form></div></div>""")
    return render_template_string(BASE,title="Log in",body=body)
@app.route("/logout")
def logout():session.clear();return redirect(url_for("home"))

@app.route("/products",methods=["GET","POST"])
@auth
def products():
    if request.method=="POST":
        name=request.form.get("name","").strip();desc=request.form.get("description","").strip();price=request.form.get("price","").strip();currency=request.form.get("currency","EUR").strip().upper();avail=request.form.get("availability","in_stock");shipping=request.form.get("shipping","").strip();url=request.form.get("url","").strip();attrs=request.form.get("attributes","{}").strip()
        try:json.loads(attrs)
        except:attrs="{}"
        if not name or not desc or not price or not url:flash("Fill in product name, description, price and product URL.")
        else:
            db().execute("INSERT INTO products(user_id,name,description,price,currency,availability,shipping,url,attributes,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(me()["id"],name,desc,price,currency,avail,shipping,url,attrs,datetime.utcnow().isoformat()));db().commit();flash("Product added.");return redirect(url_for("products"))
    ps=db().execute("SELECT * FROM products WHERE user_id=? ORDER BY id DESC",(me()["id"],)).fetchall()
    body=render_template_string("""<section class="section"><div class="head"><div><div class="k">Your catalog</div><h1 style="font-size:45px;margin:7px 0">Agent-ready products.</h1><p class="muted">Normalize your product information once.</p></div></div><div class="grid2"><div class="panel"><h2>Add product</h2><form method="post"><div class="field"><label>Product name</label><input name="name" placeholder="Running Shoes X1" required></div><div class="field"><label>Description</label><textarea name="description" placeholder="Clear product description" required></textarea></div><div class="field"><label>Price</label><input name="price" placeholder="79.90" required></div><div class="field"><label>Currency</label><input name="currency" value="EUR" required></div><div class="field"><label>Availability</label><select name="availability"><option value="in_stock">In stock</option><option value="out_of_stock">Out of stock</option><option value="preorder">Pre-order</option></select></div><div class="field"><label>Shipping</label><input name="shipping" placeholder="2-4 business days"></div><div class="field"><label>Product URL</label><input name="url" type="url" placeholder="https://example.com/product" required></div><div class="field"><label>Attributes JSON</label><textarea name="attributes">{}</textarea></div><button class="btn primary">Add to catalog</button></form></div><div><h2>Current products</h2>{%if ps%}<div class="cards">{%for p in ps%}<a class="card" href="{{url_for('product',pid=p.id)}}"><div class="tag">READY</div><h3>{{p.name}}</h3><p>{{p.description[:90]}}</p><div class="row"><span>{{p.price}} {{p.currency}}</span><span class="pill">{{p.availability}}</span></div></a>{%endfor%}</div>{%else%}<div class="panel"><p class="muted">No products yet.</p></div>{%endif%}</div></div></section>""",ps=ps)
    return render_template_string(BASE,title="Products",body=body)

@app.route("/product/<int:pid>")
def product(pid):
    p=db().execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
    if not p:return "Product not found",404
    body=render_template_string("""<section class="section"><div class="grid2"><div class="panel"><div class="k">Agent-ready product</div><h1 style="font-size:53px">{{p.name}}</h1><p class="muted" style="font-size:18px;line-height:1.6">{{p.description}}</p><div class="row"><b>{{p.price}} {{p.currency}}</b><span class="pill">{{p.availability}}</span></div><p class="muted">Shipping: {{p.shipping or 'Not specified'}}</p><p><a class="btn" href="{{p.url}}" target="_blank">Open merchant product</a></p></div><div><div class="panel"><div class="k">Machine-readable record</div><pre>{{data}}</pre></div><p class="muted">This is the core output: clean, structured data that can be adapted to agent commerce standards and channels.</p></div></div></section>""",p=p,data=agent_json(p))
    return render_template_string(BASE,title=p["name"],body=body)

@app.route("/dashboard")
@auth
def dashboard():
    count=db().execute("SELECT COUNT(*) c FROM products WHERE user_id=?",(me()["id"],)).fetchone()["c"]
    body=render_template_string("""<section class="section"><div class="k">Merchant dashboard</div><h1 style="font-size:45px">Catalog status.</h1><div class="statgrid"><div class="stat"><span class="muted">Products</span><b>{{count}}</b></div><div class="stat"><span class="muted">Format</span><b>Structured</b></div><div class="stat"><span class="muted">Next layer</span><b>Channels</b></div></div><div class="panel" style="margin-top:15px"><h2>Roadmap</h2><p class="muted">Import Shopify/WooCommerce feeds → validate catalog → generate ACP/UCP-compatible endpoints → monitor AI-channel visibility → attribute AI-originated sales.</p></div></section>""",count=count)
    return render_template_string(BASE,title="Dashboard",body=body)

with app.app_context():init()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
