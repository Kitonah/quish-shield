from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from backend.database import Base


class URLRecord(Base):
    __tablename__ = "url_records"

    # Primary key for each database record
    id = Column(Integer, primary_key=True, index=True)

    # Normalized URL
    url = Column(String, nullable=False)

    # SHA-256 hash used for fast lookups
    # Unique prevents duplicate URL records
    url_hash = Column(String, unique=True, index=True, nullable=False)

    # Final classification
    status = Column(String, nullable=False)

    # Combined threat score
    threat_score = Column(Float, nullable=False)

    # Brand detected by visual analysis
    detected_brand = Column(String, nullable=True)

    # When the URL was first added
    first_seen = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Updated whenever the URL is scanned again
    last_scanned = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Number of times this URL has been scanned
    scan_count = Column(Integer, nullable=False, default=1)