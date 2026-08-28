import logging

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
            heuristic_score=record.threat_score,
            flags=["Result served from cache"],
        ),

        snapshot=SnapshotResult(
            success=True,
            resolved_url=record.url,
        ),

        visual_match=VisualMatchResult(
            matched_brand=record.detected_brand,
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
    # TODO: Replace this mock with Member 2's real function.

    heuristics = HeuristicsResult(
        heuristic_score=45.0,
        domain_age_days=4,
        is_typosquat=True,
        target_candidate="OnlineSBI",
        flags=[
            "Domain age < 7 days",
            "Suspicious TLD",
        ],
    )

    # ---------------------------------------------------------
    # 4. Member 3 - Playwright / sandbox snapshot
    # ---------------------------------------------------------
    # TODO: Replace this mock with Member 3's real function.

    snapshot = SnapshotResult(
        success=True,
        resolved_url=normalized_url,
        screenshot_path="temp_snapshots/mock.png",
        has_credential_inputs=True,
        page_title="Mock Login Page",
    )

    # ---------------------------------------------------------
    # 5. Member 4 - Visual brand matching
    # ---------------------------------------------------------
    # TODO: Replace this mock with Member 4's real function.

    visual_match = VisualMatchResult(
        matched_brand="State Bank of India",
        visual_similarity_score=92.4,
        is_visual_spoof=True,
    )

    # ---------------------------------------------------------
    # 6. Temporary threat scoring
    # ---------------------------------------------------------
    # TODO: Replace this with the final scoring/weighting system.

    threat_score = 78.5
    status = ThreatStatus.CRITICAL_PHISHING

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