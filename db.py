import os,sqlite3
from datetime import datetime,timezone
DB=os.getenv("DATABASE_PATH","yazonii.db")
SCHEMA="""CREATE TABLE IF NOT EXISTS prospects(id INTEGER PRIMARY KEY AUTOINCREMENT,domain TEXT UNIQUE NOT NULL,url TEXT NOT NULL,name TEXT,query TEXT,discovered_at TEXT NOT NULL,last_crawled_at TEXT,last_analyzed_at TEXT,status TEXT NOT NULL DEFAULT 'discovered',opportunity_score INTEGER NOT NULL DEFAULT 0,confidence INTEGER NOT NULL DEFAULT 0,category TEXT,summary TEXT,pain_points TEXT,opportunities TEXT,recommended_action TEXT,evidence TEXT,discord_sent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,queries TEXT NOT NULL,discovered INTEGER DEFAULT 0,analyzed INTEGER DEFAULT 0,sent INTEGER DEFAULT 0);"""
def conn():
 c=sqlite3.connect(DB,timeout=30);c.row_factory=sqlite3.Row;return c
def now():return datetime.now(timezone.utc).isoformat()
def init_db():
 c=conn();c.executescript(SCHEMA);c.commit();c.close()
def upsert_prospect(domain,url,name="",query=""):
 c=conn();c.execute("""INSERT INTO prospects(domain,url,name,query,discovered_at) VALUES(?,?,?,?,?) ON CONFLICT(domain) DO UPDATE SET url=excluded.url,name=COALESCE(NULLIF(excluded.name,''),prospects.name),query=COALESCE(NULLIF(excluded.query,''),prospects.query)""",(domain,url,name,query,now()));c.commit();r=c.execute("SELECT * FROM prospects WHERE domain=?",(domain,)).fetchone();c.close();return r
def update_prospect(domain,**fields):
 allowed={"name","last_crawled_at","last_analyzed_at","status","opportunity_score","confidence","category","summary","pain_points","opportunities","recommended_action","evidence","discord_sent","url"}
 fields={k:v for k,v in fields.items() if k in allowed}
 if not fields:return
 c=conn();c.execute("UPDATE prospects SET "+",".join(f"{k}=?" for k in fields)+" WHERE domain=?",list(fields.values())+[domain]);c.commit();c.close()
def list_prospects(limit=100):
 c=conn();r=c.execute("SELECT * FROM prospects ORDER BY opportunity_score DESC,discovered_at DESC LIMIT ?",(limit,)).fetchall();c.close();return r
def get_stats():
 c=conn();total=c.execute("SELECT COUNT(*) FROM prospects").fetchone()[0];analyzed=c.execute("SELECT COUNT(*) FROM prospects WHERE last_analyzed_at IS NOT NULL").fetchone()[0];sent=c.execute("SELECT COUNT(*) FROM prospects WHERE discord_sent=1").fetchone()[0];high=c.execute("SELECT COUNT(*) FROM prospects WHERE opportunity_score>=75").fetchone()[0];c.close();return {"prospects":total,"analyzed":analyzed,"sent":sent,"high":high}
def save_scan(queries,result):
 c=conn();c.execute("INSERT INTO scans(created_at,queries,discovered,analyzed,sent) VALUES(?,?,?,?,?)",(now(),", ".join(queries),result.get("discovered",0),result.get("analyzed",0),result.get("sent",0)));c.commit();c.close()