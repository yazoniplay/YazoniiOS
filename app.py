import os,re,sqlite3,json
from datetime import datetime
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from flask import Flask,request,render_template_string

app=Flask(__name__)
DB=os.getenv("DATABASE_PATH","dropscout.db")
app.secret_key=os.getenv("SECRET_KEY","dev")

STYLE="""<style>
:root{--bg:#07080a;--panel:#101217;--line:#292d35;--text:#f4f5f7;--muted:#9499a3;--accent:#ff6a00;--green:#69d39b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px system-ui,sans-serif}.wrap{max-width:1050px;margin:auto;padding:0 20px}nav{height:68px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}.brand{font-weight:950;font-size:19px}.brand span{color:var(--accent)}a{color:inherit;text-decoration:none}.hero{padding:80px 0 45px;max-width:850px}.eyebrow{color:#ff9a55;text-transform:uppercase;font-size:12px;font-weight:850;letter-spacing:1.5px}h1{font-size:clamp(42px,7vw,72px);line-height:.98;letter-spacing:-3px;margin:12px 0 18px}.lead{font-size:19px;color:var(--muted);line-height:1.55}.form{display:flex;gap:8px;margin:25px 0}.form input{flex:1;min-width:0;background:#0c0e12;border:1px solid var(--line);border-radius:10px;padding:13px;color:white}.btn{border:1px solid var(--line);background:#171a20;color:white;border-radius:10px;padding:12px 17px;font-weight:800;cursor:pointer}.primary{background:var(--accent);border-color:var(--accent);color:#101010}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:22px}.price{font-size:40px;font-weight:950}.muted{color:var(--muted)}.tag{display:inline-block;background:#1d130d;color:#ffad76;padding:5px 9px;border-radius:999px;font-size:11px;font-weight:800}.history{margin-top:20px}.row{display:flex;justify-content:space-between;gap:15px;padding:14px 0;border-top:1px solid var(--line)}.green{color:var(--green)}.small{font-size:13px}.error{border:1px solid #653434;background:#211112;padding:14px;border-radius:10px;color:#ff9b9b}.footer{padding:35px 0;color:var(--muted);font-size:12px;border-top:1px solid var(--line);margin-top:50px}@media(max-width:700px){.grid{grid-template-columns:1fr}.form{flex-direction:column}}
</style>"""
BASE="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} · DropScout</title>"""+STYLE+"""</head><body><div class="wrap"><nav><a class="brand" href="/">DROPSCOUT<span>.</span></a><span class="muted small">Price intelligence</span></nav>{{body|safe}}<footer class="footer">Prices are read from publicly available product pages. Always verify the final price at the retailer.</footer></div></body></html>"""

def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c

def init():
 c=conn();c.execute("CREATE TABLE IF NOT EXISTS watches(id INTEGER PRIMARY KEY AUTOINCREMENT,url TEXT NOT NULL,domain TEXT NOT NULL,title TEXT,price REAL,currency TEXT,created_at TEXT NOT NULL)");c.commit();c.close()

def extract(url):
 if not re.match(r"^https?://",url):url="https://"+url
 req=Request(url,headers={"User-Agent":"Mozilla/5.0 DropScout/1.0"})
 with urlopen(req,timeout=10) as r:
  html=r.read(900000).decode("utf-8","ignore");final=r.geturl()
 title=""
 m=re.search(r"<title[^>]*>(.*?)</title>",html,re.I|re.S)
 if m:title=re.sub(r"\s+"," ",m.group(1)).strip()[:180]
 currency="";price=None
 ld=re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',html,re.I|re.S)
 for block in ld:
  try:
   data=json.loads(block)
   items=data if isinstance(data,list) else [data]
   stack=items[:]
   while stack:
    x=stack.pop()
    if isinstance(x,dict):
     offers=x.get("offers")
     if isinstance(offers,dict):
      p=offers.get("price")
      if p is not None:
       try:price=float(str(p).replace(",",""));currency=str(offers.get("priceCurrency") or "")
       except:pass
       if price is not None:break
     for v in x.values():
      if isinstance(v,(dict,list)):stack.extend(v if isinstance(v,list) else [v])
    elif isinstance(x,list):stack.extend(x)
   if price is not None:break
  except:pass
 if price is None:
  patterns=[
   r'itemprop=["\']price["\'][^>]*content=["\']([0-9]+(?:[.,][0-9]{1,2})?)',
   r'["\']price["\']\s*[:=]\s*["\']?([0-9]+(?:[.,][0-9]{1,2})?)'
  ]
  for ptn in patterns:
   m=re.search(ptn,html,re.I)
   if m:
    try:price=float(m.group(1).replace(",","."));break
    except:pass
 if not currency:
  m=re.search(r'itemprop=["\']priceCurrency["\'][^>]*content=["\']([A-Z]{3})',html,re.I)
  if m:currency=m.group(1).upper()
 domain=urlparse(final).netloc
 return {"url":final,"domain":domain,"title":title or domain,"price":price,"currency":currency or "","checked":datetime.utcnow().isoformat()}

@app.route("/",methods=["GET","POST"])
def home():
 result=None;error=None;history=[]
 if request.method=="POST":
  url=request.form.get("url","").strip()
  if url:
   try:
    result=extract(url)
    if result["price"] is None: error="I could open the page, but I couldn't reliably find a product price. Try a product page with structured price data."
    else:
     c=conn();c.execute("INSERT INTO watches(url,domain,title,price,currency,created_at) VALUES(?,?,?,?,?,?)",(result["url"],result["domain"],result["title"],result["price"],result["currency"],result["checked"]));c.commit()
     history=c.execute("SELECT * FROM watches WHERE url=? ORDER BY id DESC LIMIT 10",(result["url"],)).fetchall();c.close()
   except Exception as e:error="Could not read that page. Check the URL and try again."
 body=render_template_string("""<section class="hero"><div class="eyebrow">Consumer price intelligence</div><h1>Know if the price is actually worth it.</h1><p class="lead">Paste a product link. DropScout extracts the current price, records it, and builds a simple price trail so you can spot changes instead of guessing.</p><form class="form" method="post"><input name="url" placeholder="Paste a product URL…" required><button class="btn primary">Check price</button></form>{%if error%}<div class="error">{{error}}</div>{%endif%}</section>{%if result and not error%}<section class="grid"><div class="panel"><div class="eyebrow">Current listing</div><h2>{{result.title}}</h2><div class="price">{{"%.2f"|format(result.price)}} {{result.currency}}</div><p class="muted small">{{result.domain}}</p><a class="btn" href="{{result.url}}" target="_blank">Open retailer ↗</a></div><div class="panel"><div class="eyebrow">Price trail</div>{%if history|length>1%}<p class="green">Price history captured.</p>{%else%}<p>No history yet. Check this product again after the price changes.</p>{%endif%}{%for x in history%}<div class="row"><span class="muted small">{{x.created_at[:16].replace("T"," ")}} UTC</span><b>{{"%.2f"|format(x.price)}} {{x.currency}}</b></div>{%endfor%}</div></section>{%endif%}<section class="grid" style="margin-top:14px"><div class="panel"><span class="tag">NEXT</span><h3>Automatic tracking</h3><p class="muted">Turn one-time checks into watchlists, scheduled rechecks and price-drop alerts.</p></div><div class="panel"><span class="tag">BUSINESS MODEL</span><h3>Free → Pro</h3><p class="muted">Free checks. Paid monitoring and alerts. Long-term expansion can add retailer comparison and affiliate commerce.</p></div></section>""",result=result,error=error,history=history)
 return render_template_string(BASE,title="Price tracker",body=body)

init()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
