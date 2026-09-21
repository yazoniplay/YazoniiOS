import logging
import os

from db import init_db, save_scan
from pipeline import run_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    raw_queries = os.getenv("DEFAULT_QUERIES", "").strip()
    if not raw_queries:
        raw_queries = "dentist stockholm,restaurant stockholm,construction company stockholm"
    queries = [item.strip() for item in raw_queries.split(",") if item.strip()]
    init_db()
    result = run_scan(queries)
    save_scan(queries, result)
    logging.info("YazoniiOS scan completed: %s", result)


if __name__ == "__main__":
    main()
