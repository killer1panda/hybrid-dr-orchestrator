import os
import time
import logging
import signal
from sqlalchemy import text
from app.database import engine, Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s [RPO-PROBE] %(levelname)s: %(message)s")
logger = logging.getLogger("rpo_probe")
NODE_NAME = os.getenv("NODE_NAME", "onprem-db-primary")
running = True

def handle_exit(signum, frame):
    global running
    logger.info("Signal %s received; terminating probe cleanly...", signum)
    running = False

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

def main():
    logger.info("Initializing RPO probe daemon on %s...", NODE_NAME)
    Base.metadata.create_all(bind=engine)
    insert_sql = text("INSERT INTO rpo_probe (cluster_node) VALUES (:node) RETURNING probe_id, written_at_utc")
    consecutive_failures = 0

    while running:
        start_time = time.monotonic()
        try:
            with engine.connect() as conn:
                with conn.begin():
                    result = conn.execute(insert_sql, {"node": NODE_NAME})
                    row = result.fetchone()
                    if row and row[0] % 10 == 0:
                        logger.info("Probe tick: probe_id=%d, ts=%s", row[0], row[1])
                    consecutive_failures = 0
        except Exception as exc:
            consecutive_failures += 1
            logger.warning("Failed probe tick (%d consecutive): %s", consecutive_failures, exc)
            if consecutive_failures >= 30:
                time.sleep(2.0)
        elapsed = time.monotonic() - start_time
        time.sleep(max(0.0, 1.0 - elapsed))
    logger.info("RPO probe stopped.")

if __name__ == "__main__":
    main()
