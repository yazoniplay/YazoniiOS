import os,re,sqlite3,urllib.request
from datetime import datetime
from flask import Flask,g,request,render_template_string

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY","dev-only-change-me")
DB_PATH=os.getenv("DATABASE_PATH","accesspulse.db")

CSS="""<style>
:root{--bg:#08090b;--p:#111318;--l:#292d35;--t:#f5f5f2;--m:#969aa3;--a:#ff6a00;--good:#65d391;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--t);font:15px Inter,system-ui,sans-serif}.shell{max-width:1100px;margin:auto;padding:0 22px}
nav{height:70px;border-bottom:1px solid var(--l);display:flex;align-items:center;justify-content:space-between}.logo{font-weight:950;font-size:20px}.logo i{color:var(--a);font-style:normal}
.btn{display:inline-block;padding:11px 15px;border:1px solid var(--l);border-radius:9px;background:#171a20;color:#fff;cursor:pointer}.primary{background:var(--a);border-color:var(--a);color:#111;font-weight:850}
.hero{padding:85px 0 60px;max-width:880px}.k{font-size:12px;letter-spacing:1.5px;text-transform:uppercase;color:#ff9a4d;font-weight:850}h1{font-size:clamp(44px,7vw,76px);line-height:.98;letter-spacing:-3px;margin:14px 0 20px}.hero p{font-size:19px;color:var(--m);line-height:1.55}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:25px}
.form{display:flex;gap:8px;margin:25px 0}.form input{flex:1;background:#0c0d10;border:1px solid var(--l);color:#fff;padding:12px;border-radius:9px}.panel{background:var(--p);border:1px solid var(--l);border-radius:15px;padding:23px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.score{font-size:40px;font-weight:950}.good{color:var(--good)}.bad{color:var(--bad)}.warn{color:#ffb15c}.muted{color:var(--m)}.issue{border-top:1px solid var(--l);padding:15px 0}.issue:first-child{border-top:0}.tag{display:inline-block;border-radius:999px;padding:4px 8px;font-size:11px;background:#1c120c;color:#ffad75}
.statgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}.stat{background:var(--p);border:1px solid var(--l);border-radius:13px;padding:18px}.stat b{display:block;font-size:27px;margin-top:5px}.footer{border-top:1px solid var(--l);padding:28px 0;color:var(--m);font-size:13px}
@media(max-width:700px){.grid,.statgrid{grid-template-columns:1fr}}
</style>"""
BASE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · AccessPulse</title>"""+CSS+"""</head><body><div class="shell"><nav><a class="logo" href="/">ACCESSPULSE<i>.</i></a><span class="muted">EU accessibility monitor</span></nav>{{body|safe}}<footer class="footer">Automated checks are indicators, not legal certification.</footer></div></body></html>"""

def db():
 if "db" not in g:g.db=sqlite3.connect(DB_PATH);g.db.row_factory=sqlite3.Row
 return g.db
@app.teardown_appcontext
def close(e):
 c=g.pop("db",None)
 if c:c.close()
def init():
 c=sqlite3.connect(DB_PATH);c.execute("CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY AUTOINCREMENT,url TEXT NOT NULL,score INTEGER NOT NULL,issues TEXT NOT NULL,created_at TEXT NOT NULL)");c.commit();c.close()

def scan(url):
 if not re.match(r"^https?://",url):url="https://"+url
 try:
  req=urllib.request.Request(url,headers={"User-Agent":"AccessPulse/1.0 accessibility checker"})
  with urllib.request.urlopen(req,timeout=8) as r: raw=r.read(700000).decode("utf-8","ignore"); status=r.status; final=r.geturl()
 except Exception as e:return {"error":str(e)}
 issues=[]
 def add(key,severity,msg,fix):issues.append({"key":key,"severity":severity,"msg":msg,"fix":fix})
 imgs=re.findall(r"<img\b[^>]*>",raw,re.I)
 missing=[x for x in imgs if not re.search(r'\balt\s*=',x,re.I)]
 if missing:add("IMG_ALT","high",f"{len(missing)} image(s) appear to be missing alt attributes.","Add meaningful alt text to informative images; use empty alt for decorative images.")
 if not re.search(r"<html\b[^>]*\blang\s*=",raw,re.I):add("HTML_LANG","medium","The <html> element has no lang attribute.","Add the page language, e.g. <html lang="en">.")
 if not re.search(r"<title\b[^>]*>.*?</title>",raw,re.I|re.S):add("TITLE","high","No HTML title element was detected.","Add a concise, descriptive <title>.")
 headings=re.findall(r"<h([1-6])\b",raw,re.I)
 if not headings:add("HEADINGS","medium","No heading elements were detected.","Use a logical heading structure to describe page sections.")
 if not re.search(r"<main\b",raw,re.I):add("LANDMARK_MAIN","low","No <main> landmark was detected.","Wrap the primary page content in a <main> landmark.")
 if not re.search(r"""<meta\b[^>]*name=["']viewport""",raw,re.I):add("VIEWPORT","low","No responsive viewport meta tag was detected.","Add a viewport meta tag for mobile accessibility.")
 if re.search(r"<input\b",raw,re.I) and not re.search(r"<label\b",raw,re.I):add("FORM_LABELS","high","Form controls were detected but no label element was found.","Associate every form control with a visible label.")
 if re.search(r"(<a\b[^>]*>\s*</a>|<button\b[^>]*>\s*</button>)",raw,re.I|re.S):add("EMPTY_CONTROLS","medium","An apparently empty link or button was detected.","Give interactive controls an accessible name.")
 if re.search(r"<marquee\b|blink\b",raw,re.I):add("OBSOLETE_MOTION","medium","Obsolete motion elements were detected.","Replace obsolete motion elements with accessible, user-controlled alternatives.")
 score=max(0,100-len(issues)*12-sum(8 for x in issues if x["severity"]=="high"))
 return {"status":status,"final":final,"score":score,"issues":issues}

@app.route("/",methods=["GET","POST"])
def home():
 result=None
 if request.method=="POST":
  url=request.form.get("url","").strip()
  if url:
   result=scan(url)
   if "error" not in result:
    db().execute("INSERT INTO scans(url,score,issues,created_at) VALUES(?,?,?,?)",(url,result["score"],str(result["issues"]),datetime.utcnow().isoformat()));db().commit()
 body=render_template_string("""<section class="hero"><div class="k">Accessibility monitoring</div><h1>Find accessibility problems before your customers do.</h1><p>Enter a public URL. AccessPulse runs a fast automated accessibility pre-check and turns the result into a clear fix list.</p><form class="form" method="post"><input name="url" placeholder="https://yourstore.com" required><button class="btn primary">Scan website</button></form><p class="muted">Built for the EU market, where the European Accessibility Act applies to covered products and services including e-commerce.</p></section>
{%if result%}{%if result.error%}<div class="panel"><h2>Scan failed</h2><p class="muted">{{result.error}}</p></div>{%else%}<section class="grid"><div class="panel"><div class="k">Automated result</div><div class="score {{'good' if result.score>=80 else 'warn' if result.score>=60 else 'bad'}}">{{result.score}}/100</div><p class="muted">{{result.final}}</p><p><span class="tag">{{result.issues|length}} detected issue(s)</span></p></div><div class="panel"><div class="k">What to fix</div>{%if result.issues%}{%for x in result.issues%}<div class="issue"><span class="tag">{{x.severity}}</span><b>{{x.msg}}</b><p class="muted">{{x.fix}}</p></div>{%endfor%}{%else%}<h3>No issues detected by these checks.</h3><p class="muted">Automated checks cannot prove full conformance.</p>{%endif%}</div></section>{%endif%}{%endif%}
<section class="statgrid"><div class="stat"><span class="muted">Checks</span><b>Automated</b></div><div class="stat"><span class="muted">Output</span><b>Fix list</b></div><div class="stat"><span class="muted">Positioning</span><b>EU-first</b></div></section>""",result=result)
 return render_template_string(BASE,title="Website scanner",body=body)

with app.app_context():init()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
