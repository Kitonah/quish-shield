from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


# ---------------------------------------------------------
# Enums
# ---------------------------------------------------------

class ThreatStatus(str, Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    CRITICAL_PHISHING = "CRITICAL_PHISHING"


# ---------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------

class ScanURLRequest(BaseModel):
    url: str


class ScanSMSRequest(BaseModel):
    message: str


# ---------------------------------------------------------
# Sub-module Response Schemas
# ---------------------------------------------------------

class HeuristicsResult(BaseModel):
    heuristic_score: float = 0.0
    domain_age_days: Optional[int] = None
    is_typosquat: bool = False
    target_candidate: Optional[str] = None
    flags: List[str] = []


class SnapshotResult(BaseModel):
    success: bool = True
    resolved_url: Optional[str] = None
    screenshot_path: Optional[str] = None
    has_credential_inputs: bool = False
    is_security_interstitial: bool = False
    page_title: Optional[str] = None
    error: Optional[str] = None


class VisualMatchResult(BaseModel):
    matched_brand: Optional[str] = None
    visual_similarity_score: float = 0.0
    is_visual_spoof: bool = False


# ---------------------------------------------------------
# QR / SMS Extraction Schemas
# ---------------------------------------------------------

class QRScanResponse(BaseModel):
    success: bool = True
    type: Optional[str] = None
    payload: Optional[str] = None
    resolved_url: Optional[str] = None
    error: Optional[str] = None


class SMSScanResponse(BaseModel):
    success: bool = True
    extracted_urls: List[str] = []
    primary_url: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------
# Central Orchestration Response Schema
# ---------------------------------------------------------

class ScanResponse(BaseModel):
    scan_id: str
    submitted_url: str
    source_type: str = "url"
    threat_score: float
    status: str
    detected_brand: Optional[str] = None
    heuristics: Optional[HeuristicsResult] = None
    snapshot: Optional[SnapshotResult] = None
    visual_match: Optional[VisualMatchResult] = None