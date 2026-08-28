import logging

try:
    from backend.heuristics import inspect_heuristics
except Exception:
    inspect_heuristics = None

try:
    from backend.sandbox import capture_snapshot
except Exception:
    capture_snapshot = None

try:
    from backend.visual_matcher import BrandVisualMatcher
except Exception:
    BrandVisualMatcher = None

from backend.database import (
    hash_url,
    lookup_url,
    normalize_url,
    save_or_update_result,
)
from backend.schemas import (
    HeuristicsResult,
    ScanResponse,
    SnapshotResult,
    ThreatStatus,
    VisualMatchResult,
)

logger = logging.getLogger("quishshield")
visual_matcher = BrandVisualMatcher() if BrandVisualMatcher else None


def _record_to_scan_response(record) -> ScanResponse:
    """
    Convert a cached database record into the API's ScanResponse format.

    The current database stores the final verdict and detected brand,
    but not the complete Member 2/3/4 analysis breakdown. Therefore,
    cached responses use lightweight placeholders for those sections.
    """

    return ScanResponse(
        scan_id=f"cached-{record.id}",
        submitted_url=record.url,
        threat_score=record.threat_score,
        status=ThreatStatus(record.status),

        heuristics=HeuristicsResult(
            heuristic_score=0.0,
            flags=["Detailed analysis unavailable for cached result"],
        ),

        snapshot=SnapshotResult(
            success=False,
            resolved_url=record.url,
            error="Detailed sandbox result unavailable for cached result",
        ),

        visual_match=VisualMatchResult(
            matched_brand=record.detected_brand,
            detail="Detailed visual match unavailable for cached result",
        ),
    )


async def analyze_url(url: str) -> ScanResponse:
    """
    Central orchestration pipeline for URL scanning.

    1. Normalize the URL.
    2. Hash it.
    3. Check the database cache.
    4. If found, return the cached result.
    5. If not found, run Members 2/3/4 analysis.
    6. Calculate the final threat result.
    7. Save the result to the database.
    8. Return ScanResponse.
    """

    # ---------------------------------------------------------
    # 1. Normalize and hash URL
    # ---------------------------------------------------------

    normalized_url = normalize_url(url)
    url_hash = hash_url(normalized_url)

    # ---------------------------------------------------------
    # 2. Database lookup
    # ---------------------------------------------------------

    cached_record = lookup_url(url_hash)

    if cached_record:
        logger.info(
            "CACHE HIT: returning stored result for %s",
            normalized_url,
        )

        return _record_to_scan_response(cached_record)

    logger.info(
        "CACHE MISS: running analysis for %s",
        normalized_url,
    )

    # ---------------------------------------------------------
    # 3. Member 2 - Heuristics / WHOIS / lexical analysis
    # ---------------------------------------------------------
    try:
        heuristic_data = (
            await inspect_heuristics(normalized_url)
            if inspect_heuristics
            else None
        )
        if heuristic_data is None:
            raise RuntimeError("Heuristic analyzer is unavailable")
    except Exception as exc:
        logger.exception("Heuristic scan failed for %s", normalized_url)
        heuristic_data = {
            "heuristic_score": 0.0,
            "domain_age_days": None,
            "is_typosquat": False,
            "target_candidate": None,
            "flags": [f"Heuristic analysis unavailable: {exc}"],
        }

    try:
        heuristics = HeuristicsResult(
            heuristic_score=heuristic_data.get("heuristic_score", 0.0),
            domain_age_days=heuristic_data.get("domain_age_days"),
            is_typosquat=heuristic_data.get("is_typosquat", False),
            target_candidate=heuristic_data.get("target_candidate"),
            flags=heuristic_data.get("flags", []),
        )
    except Exception as exc:
        logger.exception("Invalid heuristic result for %s", normalized_url)
        heuristics = HeuristicsResult(
            heuristic_score=0.0,
            flags=[f"Invalid heuristic result: {exc}"],
        )

    # ---------------------------------------------------------
    # 4. Member 3 - Playwright / sandbox snapshot
    # ---------------------------------------------------------
    sandbox_url = normalized_url
    if not sandbox_url.startswith(("http://", "https://")):
        sandbox_url = f"http://{sandbox_url}"

    try:
        sandbox_result = (
            await capture_snapshot(sandbox_url)
            if capture_snapshot
            else None
        )
        if sandbox_result is None:
            raise RuntimeError("Sandbox analyzer is unavailable")
    except Exception as exc:
        logger.exception("Sandbox scan failed for %s", normalized_url)
        sandbox_result = {
            "final_url": sandbox_url,
            "error": str(exc),
            "credential_fields": {},
        }

    credential_fields = sandbox_result.get("credential_fields", {})

    snapshot = SnapshotResult(
        success=sandbox_result.get("error") is None,
        resolved_url=sandbox_result.get("final_url"),
        screenshot_path=sandbox_result.get("screenshot_path"),
        redirected=sandbox_result.get("redirected", False),
        redirect_chain=sandbox_result.get("redirect_chain", []),
        page_description=sandbox_result.get("page_description"),
        load_time_ms=sandbox_result.get("load_time_ms", 0),
        has_credential_inputs=(
            credential_fields.get("has_password_field", False)
            or credential_fields.get("has_otp_field", False)
            or credential_fields.get("has_card_field", False)
            or credential_fields.get("has_login_field", False)
        ),
        suspicious_inputs=credential_fields.get("suspicious_inputs", []),
        page_title=sandbox_result.get("page_title", ""),
        error=sandbox_result.get("error"),
    )

    # ---------------------------------------------------------
    # 5. Member 4 - Visual brand matching
    # ---------------------------------------------------------
    try:
        match_result = visual_matcher.compare_snapshot(
            screenshot_path=snapshot.screenshot_path,
            final_url=snapshot.resolved_url or sandbox_url,
            page_title=snapshot.page_title or "",
        ) if visual_matcher else None
    except Exception as exc:
        logger.exception("Visual matching failed for %s", normalized_url)
        match_result = None

    visual_match = VisualMatchResult(
        matched_brand=match_result.matched_brand if match_result else None,
        visual_similarity_score=(match_result.confidence * 100) if match_result else 0.0,
        is_visual_spoof=match_result.is_spoof if match_result else False,
        domain_matches=match_result.domain_matches if match_result else True,
        detail=(match_result.detail if match_result else "Visual analysis unavailable."),
        method=match_result.method if match_result else None,
    )

    # ---------------------------------------------------------
    # 6. Temporary threat scoring
    # ---------------------------------------------------------
    credential_risk = 100.0 if snapshot.has_credential_inputs else 0.0
    visual_risk = (
        visual_match.visual_similarity_score
        if visual_match.is_visual_spoof
        else 0.0
    )
    weighted_score = (
        0.45 * heuristics.heuristic_score
        + 0.35 * visual_risk
        + 0.20 * credential_risk
    )
    evidence_floor = 0.0
    if heuristics.is_typosquat:
        evidence_floor = 40.0
    if snapshot.has_credential_inputs:
        evidence_floor = max(evidence_floor, 45.0)
    if visual_match.is_visual_spoof:
        evidence_floor = max(evidence_floor, 60.0)

    threat_score = round(min(
        max(weighted_score, evidence_floor),
        100.0,
    ), 1)

    if threat_score >= 60:
        status = ThreatStatus.CRITICAL_PHISHING
    elif threat_score >= 30:
        status = ThreatStatus.SUSPICIOUS
    else:
        status = ThreatStatus.SAFE

    # ---------------------------------------------------------
    # 7. Save result to database
    # ---------------------------------------------------------

    record = save_or_update_result(
        url=normalized_url,
        url_hash=url_hash,
        status=status.value,
        threat_score=threat_score,
        detected_brand=visual_match.matched_brand,
    )

    # ---------------------------------------------------------
    # 8. Return final API response
    # ---------------------------------------------------------

    return ScanResponse(
        scan_id=f"scan-{record.id}",
        submitted_url=url,
        threat_score=threat_score,
        status=status,
        heuristics=heuristics,
        snapshot=snapshot,
        visual_match=visual_match,
    )