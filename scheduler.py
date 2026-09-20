import os
from apscheduler.schedulers.background import BackgroundScheduler
_started=False
def start_scheduler():
 global _started
 if _started:return
 _started=True
 from pipeline import run_scan
 from db import save_scan
 queries=[x.strip() for x in os.getenv("DEFAULT_QUERIES","").split(",") if x.strip()]
 if not queries:return
 scheduler=BackgroundScheduler(daemon=True)
 def job():
  try:
   result=run_scan(queries);save_scan(queries,result)
  except Exception:pass
 scheduler.add_job(job,"interval",minutes=max(5,int(os.getenv("DISCOVERY_INTERVAL_MINUTES","60"))),id="yazoniiios-discovery",replace_existing=True)
 scheduler.start()