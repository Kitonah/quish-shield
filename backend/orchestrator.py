from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Dict

import tldextract

from backend.database import (
    hash_url,
    lookup_url,
    normalize_url,
    save_or_update_result,
)
from backend.heuristics import inspect_heuristics
from backend.sandbox import capture_snapshot
from backend.schemas import (
    HeuristicsResult,
    ScanResponse,
    SnapshotResult,
    ThreatStatus,
    VisualMatchResult,
)
from backend.visual_matcher import compare_snapshot

# Root domains that are verified legitimate ecosystems
GLOBAL_TRUSTED_ROOTS = {
    "youtube.com", "google.com", "google.co.in", 
    "amazon.in", "amazon.com", "media-amazon.com",
    "flipkart.com", "microsoft.com", "apple.com", "github.com",
    "onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com",
    "paytm.com", "phonepe.com", "incometax.gov.in"
}


def _record_to_scan_response(record) -> ScanResponse:
    """Safely constructs a ScanResponse from a cached database record without schema errors."""
    threat_score = float(record.threat_score or 0.0)
    
    return ScanResponse(
        scan_id=f"cached-{record.id}",
        submitted_url=record.url,
        source_type="url",
        threat_score=threat_score,
        status=str(record.status),
        detected_brand=record.detected_brand,
        heuristics=HeuristicsResult(
            heuristic_score=threat_score,
            domain_age_days=None,
            is_typosquat=False,
            target_candidate=record.detected_brand,
            entropy=0.0,
            flags=["Result served from indexed SHA-256 database cache"],
        ),
        snapshot=SnapshotResult(
            success=True,
            resolved_url=record.url,
            screenshot_path=None,
            has_credential_inputs=False,
            is_security_interstitial=False,
            page_title=None,
            load_time_ms=0.0,
            error=None,
        ),
        visual_match=VisualMatchResult(
            matched_brand=record.detected_brand,
            visual_similarity_score=0.0,
            is_visual_spoof=False,
            detection_method="database_cache",
            explanation="Record retrieved from pre-computed scan history.",
        ),
    )


async def analyze_url(raw_url: str) -> ScanResponse:
    normalized = normalize_url(raw_url)
    url_hash_val = hash_url(normalized)

    # 1. Check Database Cache
    cached_record = lookup_url(url_hash_val)
    if cached_record:
        return _record_to_scan_response(cached_record)

    ext = tldextract.extract(normalized)
    registered_domain = f"{ext.domain}.{ext.suffix}".lower() if ext.domain and ext.suffix else ""

    # 2. Concurrently run Network Forensics and Isolated Sandbox
    heuristics_task = inspect_heuristics(normalized)
    sandbox_task = capture_snapshot(normalized)

    heuristics_data, snapshot_data = await asyncio.gather(heuristics_task, sandbox_task)

    resolved_destination = snapshot_data.get("resolved_url") or normalized
    page_title = snapshot_data.get("page_title") or ""
    screenshot_path = snapshot_data.get("screenshot_path")

    # 3. Visual AI & Brand Verification
    match_result = compare_snapshot(
        screenshot_path=screenshot_path,
        final_url=resolved_destination,
        page_title=page_title,
    )

    visual_data: Dict[str, Any] = {
        "matched_brand": match_result.matched_brand,
        "visual_similarity_score": round(match_result.confidence * 100.0, 1),
        "is_visual_spoof": match_result.is_spoof,
        "detection_method": match_result.method,
        "explanation": match_result.detail,
    }

    # 4. Multi-Vector Composite Threat Calculation
    h_score = float(heuristics_data.get("heuristic_score", 0.0))
    is_spoof = visual_data.get("is_visual_spoof", False)
    has_creds = snapshot_data.get("has_credential_inputs", False)
    is_interstitial = snapshot_data.get("is_security_interstitial", False)
    has_sandbox_error = bool(snapshot_data.get("error"))

    total_score = h_score

    # Visual brand clone detection
    if is_spoof:
        total_score += 45.0

    # Active credential harvesting fields
    if has_creds:
        total_score += 25.0

    # Distinguish active takedown warnings from dead DNS resolution failures
    if is_interstitial:
        if has_sandbox_error:
            # Domain failed to connect or dropped connection
            total_score += 30.0
            heuristics_data["flags"].append("Host dropped connection or failed DNS resolution")
        else:
            # Active platform takedown banner rendered on-screen
            total_score += 65.0
            heuristics_data["flags"].append("Platform warning interstitial detected (Deceptive Site Ahead)")

    # Authentic Domain Protection
    if registered_domain in GLOBAL_TRUSTED_ROOTS and not heuristics_data.get("is_typosquat"):
        total_score = 0.0
        visual_data["is_visual_spoof"] = False

    final_score = min(round(total_score, 1), 100.0)

    # 5. Verdict Classification
    if final_score >= 70.0 or visual_data.get("is_visual_spoof"):
        status_enum = ThreatStatus.CRITICAL_PHISHING
    elif final_score >= 30.0:
        status_enum = ThreatStatus.SUSPICIOUS
    else:
        status_enum = ThreatStatus.SAFE

    detected_brand = visual_data.get("matched_brand") or heuristics_data.get("target_candidate")

    # 6. Persist Result in Database
    saved_record = save_or_update_result(
        url=normalized,
        url_hash=url_hash_val,
        status=status_enum.value,
        threat_score=final_score,
        detected_brand=detected_brand,
    )

    return ScanResponse(
        scan_id=f"scan-{saved_record.id if saved_record else uuid.uuid4().hex[:6]}",
        submitted_url=normalized,
        source_type="url",
        threat_score=final_score,
        status=status_enum.value,
        detected_brand=detected_brand,
        heuristics=HeuristicsResult(**heuristics_data),
        snapshot=SnapshotResult(**snapshot_data),
        visual_match=VisualMatchResult(**visual_data),
    )