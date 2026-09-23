from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_HOSTNAME = os.getenv("DATABASE_HOSTNAME")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

if all((DATABASE_HOSTNAME, DATABASE_PORT, DATABASE_NAME, DATABASE_USERNAME, DATABASE_PASSWORD)):
    DATABASE_URL = (
        f"postgresql://{DATABASE_USERNAME}:"
        f"{quote_plus(DATABASE_PASSWORD)}@"
        f"{DATABASE_HOSTNAME}:{DATABASE_PORT}/"
        f"{DATABASE_NAME}"
    )
    engine = create_engine(DATABASE_URL)
else:
    # Anchor SQLite to an absolute path inside backend/
    DB_FILE = BASE_DIR / "quishshield.db"
    DATABASE_URL = f"sqlite:///{DB_FILE}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 15},
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create database tables when the application starts."""
    try:
        from . import models  # noqa: F401
    except (ImportError, ValueError):
        import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def normalize_url(url: str) -> str:
    """Perform basic URL normalization for cache key lookup."""
    return url.strip().rstrip("/")


def hash_url(normalized_url: str) -> str:
    """Generate SHA-256 hash for database indexed query."""
    return hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()


def lookup_url(url_hash: str):
    """Query cache for an existing URL record and increment hit count."""
    try:
        from .models import URLRecord
    except (ImportError, ValueError):
        from models import URLRecord

    db = SessionLocal()
    try:
        record = (
            db.query(URLRecord)
            .filter(URLRecord.url_hash == url_hash)
            .first()
        )
        if record:
            record.scan_count += 1
            record.last_scanned = func.now()
            db.commit()
            db.refresh(record)
        return record
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()


def save_or_update_result(
    *,
    url: str,
    url_hash: str,
    status: str,
    threat_score: float,
    detected_brand: Optional[str] = None,
):
    """Store or update scan outcome in the database."""
    try:
        from .models import URLRecord
    except (ImportError, ValueError):
        from models import URLRecord

    db = SessionLocal()
    try:
        record = (
            db.query(URLRecord)
            .filter(URLRecord.url_hash == url_hash)
            .first()
        )
        if record:
            record.scan_count += 1
            record.status = status
            record.threat_score = threat_score
            record.detected_brand = detected_brand
        else:
            record = URLRecord(
                url=url,
                url_hash=url_hash,
                status=status,
                threat_score=threat_score,
                detected_brand=detected_brand,
                scan_count=1,
            )
            db.add(record)

        db.commit()
        db.refresh(record)
        return record
    except Exception:
        db.rollback()
        return None
    finally:
        db.close()