import logging
import os
from apscheduler.schedulers.background import BackgroundScheduler

from db import init_db, save_scan

_started = False
_scheduler = None
logger = logging.getLogger(__name__)


def start_scheduler():
    global _started, _scheduler
    if _started:
        return

    queries = [
        item.strip()
        for item in os.getenv("DEFAULT_QUERIES", "").split(",")
        if item.strip()
    ]
    if not queries:
        logger.warning("Scheduler disabled: DEFAULT_QUERIES is empty")
        return

    init_db()
    from pipeline import run_scan

    interval = max(10, int(os.getenv("DISCOVERY_INTERVAL_MINUTES", "10")))

    def job():
        try:
            result = run_scan(queries)
            save_scan(queries, result)
            logger.info("YazoniiOS scan completed: %s", result)
        except Exception:
            logger.exception("YazoniiOS scheduled scan failed")

    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        job,
        trigger="interval",
        minutes=interval,
        id="yazoniiios-discovery",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    _scheduler = scheduler
    _started = True

    # Run once immediately after the service starts, then continue on the interval.
    job()
