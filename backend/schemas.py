from enum import Enum
from pydantic import BaseModel, Field


class ThreatStatus(str, Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    CRITICAL_PHISHING = "CRITICAL_PHISHING"


# ---------- Frontend → Member 1 ----------

class ScanURLRequest(BaseModel):
    url: str


# ---------- Member 6 → Member 1 ----------

class ExtractionResult(BaseModel):
    success: bool
    resolved_url: str | None = None
    error: str | None = None


# ---------- Member 2 → Member 1 ----------

class HeuristicsResult(BaseModel):
    heuristic_score: float
    domain_age_days: int | None = None
    is_typosquat: bool = False
    target_candidate: str | None = None
    flags: list[str] = Field(default_factory=list)


# ---------- Member 3 → Member 1 ----------

class SnapshotResult(BaseModel):
    success: bool
    resolved_url: str | None = None
    screenshot_path: str | None = None
    redirected: bool = False
    redirect_chain: list[dict] = Field(default_factory=list)
    page_description: str | None = None
    load_time_ms: int = 0
    has_credential_inputs: bool = False
    suspicious_inputs: list[str] = Field(default_factory=list)
    page_title: str | None = None
    error: str | None = None


# ---------- Member 4 → Member 1 ----------

class VisualMatchResult(BaseModel):
    matched_brand: str | None = None
    visual_similarity_score: float = 0.0
    is_visual_spoof: bool = False
    domain_matches: bool = True
    detail: str | None = None
    method: str | None = None


# ---------- Member 1 → Frontend ----------

class ScanResponse(BaseModel):
    scan_id: str
    submitted_url: str
    threat_score: float
    status: ThreatStatus
    heuristics: HeuristicsResult
    snapshot: SnapshotResult
    visual_match: VisualMatchResult