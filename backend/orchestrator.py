from __future__ import annotations

import asyncio
import os
import uuid
from typing import Optional
from urllib.parse import urlparse

import tldextract

from backend.database import (
    hash_url,
    lookup_url,
    normalize_url,
    save_or_update_result,
)
from backend.heuristics import inspect_heuristics
from backend.schemas import (
    HeuristicsResult,
    ScanResponse,
    SnapshotResult,
    ThreatStatus,
    VisualMatchResult,
)

# Canonical domain whitelist per brand to prevent false positives
BRAND_DOMAINS = {
    "amazon": ["amazon.in", "amazon.com", "amazon.co.uk", "media-amazon.com"],
    "google": ["google.com", "google.co.in", "youtube.com", "youtu.be", "accounts.google.com", "gstatic.com"],
    "hdfc": ["hdfcbank.com", "hdfc.com"],
    "icici": ["icicibank.com"],
    "incometax": ["incometax.gov.in", "incometaxindiaefiling.gov.in"],
    "paytm": ["paytm.com"],
    "phonepe": ["phonepe.com"],
    "sbi": ["onlinesbi.sbi", "onlinesbi.com", "sbi.co.in"],
}

# Top benign ecosystem domains that should never be flagged as visual spoofs
GLOBAL_TRUSTED_ROOTS = {
    "youtube.com", "google.com", "amazon.in", "amazon.com", 
    "flipkart.com", "microsoft.com", "apple.com", "github.com"
}


def _record_to_scan_response(record) -> ScanResponse:
    """Safely construct a ScanResponse from a cached database record."""
    return ScanResponse(
        scan_id=f"cached-{record.id}",
        submitted_url=record.url,
        source_type="url",
        threat_score=float(record.threat_score or 0.0),
        status=str(record.status),
        detected_brand=record.detected_brand,
        heuristics=HeuristicsResult(
            heuristic_score=float(record.threat_score or 0.0),
            domain_age_days=None,
            is_typosquat=False,
            target_candidate=record.detected_brand,
            flags=["Result served from cache"],
        ),
        snapshot=SnapshotResult(
            success=True,
            resolved_url=record.url,
            screenshot_path=None,
            has_credential_inputs=False,
            page_title=None,
            error=None,
        ),
        visual_match=VisualMatchResult(
            matched_brand=record.detected_brand,
            visual_similarity_score=0.0,
            is_visual_spoof=False,
        ),
    )


async def analyze_url(raw_url: str) -> ScanResponse:
    """Central orchestration pipeline connecting Member 2, 3, and 4 engines."""
    normalized = normalize_url(raw_url)
    url_hash_val = hash_url(normalized)

    # 1. Check Database Cache
    cached_record = lookup_url(url_hash_val)
    if cached_record:
        return _record_to_scan_response(cached_record)

    # Extract base domain components
    ext = tldextract.extract(normalized)
    registered_domain = f"{ext.domain}.{ext.suffix}".lower() if ext.domain and ext.suffix else ""

    # 2. Member 2: Heuristics & RDAP Forensics
    heuristics_data = await inspect_heuristics(normalized)

    # 3. Member 3: Headless Sandbox
    snapshot_data = {
        "success": True,
        "resolved_url": normalized,
        "screenshot_path": None,
        "has_credential_inputs": False,
        "page_title": None,
        "error": None,
    }
    try:
        from backend.sandbox import capture_snapshot
        snap_res = await capture_snapshot(normalized)
        if snap_res:
            snapshot_data.update(snap_res)
    except Exception as e:
        snapshot_data["error"] = str(e)

    # 4. Member 4: Computer Vision Matcher
    visual_data = {
        "matched_brand": None,
        "visual_similarity_score": 0.0,
        "is_visual_spoof": False,
    }
    screenshot_path = snapshot_data.get("screenshot_path")
    if screenshot_path and os.path.exists(screenshot_path):
        try:
            from backend.visual_matcher import predict_brand
            pred_brand, conf = predict_brand(screenshot_path)
            
            if pred_brand and pred_brand.lower() != "unknown" and conf >= 85.0:
                brand_key = pred_brand.lower()
                allowed_domains = BRAND_DOMAINS.get(brand_key, [])
                
                # Verify if current domain is owned by predicted brand
                is_legit = registered_domain in allowed_domains or any(d in normalized.lower() for d in allowed_domains)
                
                visual_data["matched_brand"] = pred_brand
                visual_data["visual_similarity_score"] = round(conf, 1)
                visual_data["is_visual_spoof"] = not is_legit
        except Exception:
            pass

    # 5. Calculate Composite Threat Score
    h_score = float(heuristics_data.get("heuristic_score", 0.0))
    is_spoof = visual_data.get("is_visual_spoof", False)
    has_creds = snapshot_data.get("has_credential_inputs", False)

    total_score = h_score
    if is_spoof:
        total_score += 45.0
    if has_creds and (h_score > 20 or is_spoof):
        total_score += 20.0

    # Whitelist exemption for genuine verified domains
    if registered_domain in GLOBAL_TRUSTED_ROOTS or any(registered_domain in v for v in BRAND_DOMAINS.values()):
        if not heuristics_data.get("is_typosquat"):
            total_score = min(total_score, 0.0)
            visual_data["is_visual_spoof"] = False

    final_score = min(round(total_score, 1), 100.0)

    # 6. Assign Verdict
    if final_score >= 70.0 or visual_data.get("is_visual_spoof"):
        status_enum = ThreatStatus.CRITICAL_PHISHING
    elif final_score >= 30.0:
        status_enum = ThreatStatus.SUSPICIOUS
    else:
        status_enum = ThreatStatus.SAFE

    detected_brand = visual_data.get("matched_brand") or heuristics_data.get("target_candidate")

    # 7. Persist to Database
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