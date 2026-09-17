from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

try:
    from .database import Base
except (ImportError, ValueError):
    from database import Base


class URLRecord(Base):
    __tablename__ = "url_records"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(Text, nullable=False)
    url_hash = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(32), nullable=False)
    threat_score = Column(Float, nullable=False, default=0.0)
    detected_brand = Column(String(64), nullable=True)
    scan_count = Column(Integer, nullable=False, default=1)
    first_scanned = Column(DateTime(timezone=True), server_default=func.now())
    last_scanned = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())