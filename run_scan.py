import logging
import os

from db import init_db, save_scan
from pipeline import run_scan

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    queries = [item.strip() for item in os.getenv("DEFAULT_QUERIES", "").split(",") if item.strip()]
    if not queries:
        raise SystemExit("DEFAULT_QUERIES is empty. Configure repository variable DEFAULT_QUERIES.")
    init_db()
    result = run_scan(queries)
    save_scan(queries, result)
    logging.info("YazoniiOS scan completed: %s", result)


if __name__ == "__main__":
    main()
