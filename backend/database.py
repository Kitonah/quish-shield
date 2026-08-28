import hashlib
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func


load_dotenv(Path(__file__).with_name(".env"))

from urllib.parse import quote_plus

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
else:
    DATABASE_URL = "sqlite:///./quishshield.db"

engine_args = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_db() -> None:
    """Create database tables when the application starts."""

    from backend import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# Cache-key normalization
# ---------------------------------------------------------

def normalize_url(url: str) -> str:
    """
    Perform ONLY minimal normalization required for cache identity.

    This is NOT URL security analysis.

    We only remove:
    - surrounding whitespace
    - a trailing slash

    Security-related URL parsing and feature extraction
    belongs to Member 2.
    """

    return url.strip().rstrip("/")


# ---------------------------------------------------------
# URL hashing
# ---------------------------------------------------------

def hash_url(normalized_url: str) -> str:
    """Create a SHA-256 hash used as the database lookup key."""

    return hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------
# Database lookup
# ---------------------------------------------------------

def lookup_url(url_hash: str):
    """
    Find an existing URL record using its hash.

    Returns:
        URLRecord if found
        None if not found
    """

    from backend.models import URLRecord

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
    finally:
        db.close()


# ---------------------------------------------------------
# Save / update result
# ---------------------------------------------------------

def save_or_update_result(
    *,
    url: str,
    url_hash: str,
    status: str,
    threat_score: float,
    detected_brand: str | None,
):
    """
    Create a new URL record or update an existing one.
    """

    from backend.models import URLRecord

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

    finally:
        db.close()