import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("database")

DB_USER = os.getenv("POSTGRES_USER", "dr_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "dr_secure_password_2026")
DB_HOST = os.getenv("POSTGRES_HOST", "192.168.10.30")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "dr_app")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=10,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_db_connection() -> dict[str, str | bool]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            ro_check = conn.execute(text("SHOW default_transaction_read_only")).scalar()
            is_read_only = str(ro_check).lower() in ("on", "true", "1")
            return {
                "connected": True,
                "read_only": is_read_only,
                "status": "degraded" if is_read_only else "healthy",
            }
    except Exception as exc:
        logger.error("Database connection failure: %s", exc)
        return {"connected": False, "read_only": False, "status": "down", "error": str(exc)}
