from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.orchestrator import analyze_url
from backend.qr_decoder import QRDecoder
from backend.schemas import (
    QRScanResponse,
    ScanResponse,
    ScanSMSRequest,
    ScanURLRequest,
    SMSScanResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="QuishShield API Gateway",
    version="1.0.0",
    description="Multi-Vector Phishing, Smishing & Quishing Intelligence Engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "status": "online",
        "system": "QuishShield Security Gateway",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/scan-url", response_model=ScanResponse)
async def scan_url(request: ScanURLRequest) -> ScanResponse:
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="Target URL cannot be empty.")
    return await analyze_url(request.url)


@app.post("/api/v1/scan-qr", response_model=QRScanResponse)
async def scan_qr(file: UploadFile = File(...)) -> QRScanResponse:
    try:
        image_bytes = await file.read()
    except Exception as e:
        return QRScanResponse(
            success=False,
            found=False,
            error=f"Failed to read uploaded file: {str(e)}",
        )

    if not image_bytes:
        return QRScanResponse(
            success=False,
            found=False,
            error="Uploaded image file was empty.",
        )

    try:
        result = QRDecoder.decode_image(image_bytes)
    except Exception as e:
        return QRScanResponse(
            success=False,
            found=False,
            error=f"Error processing image: {str(e)}",
        )

    if not result or not result.get("found"):
        return QRScanResponse(
            success=False,
            found=False,
            error="No QR code could be detected in this image.",
        )

    raw_data = result.get("raw_data") or ""
    resolved_target = result.get("resolved_url") or raw_data
    is_upi = bool(result.get("is_upi", False))
    is_web_url = raw_data.startswith(("http://", "https://"))

    qr_type = "upi" if is_upi else ("url" if is_web_url else "text")

    return QRScanResponse(
        success=True,
        found=True,
        type=qr_type,
        payload=resolved_target,
        raw_data=raw_data,
        resolved_url=resolved_target if is_web_url else None,
        is_upi=is_upi,
        error=None,
    )


@app.post("/api/v1/scan-sms", response_model=SMSScanResponse)
async def scan_sms(request: ScanSMSRequest) -> SMSScanResponse:
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="SMS content cannot be empty.")

    matches = QRDecoder.parse_sms(request.message)

    if not matches:
        return SMSScanResponse(
            success=False,
            extracted_urls=[],
            primary_url=None,
            error="No suspicious link could be detected in this message.",
        )

    resolved_list = [item["resolved"] for item in matches if item.get("resolved")]
    primary = resolved_list[0] if resolved_list else None

    return SMSScanResponse(
        success=True,
        extracted_urls=resolved_list,
        primary_url=primary,
        error=None,
    )