from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.orchestrator import analyze_url
from backend.qr_decoder import QRDecoder
from backend.schemas import QRScanResponse, ScanResponse, ScanSMSRequest, ScanURLRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database when the API starts
    init_db()
    yield


app = FastAPI(
    title="QuishShield API",
    version="0.1.0",
    lifespan=lifespan,
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# URL scanning endpoint
@app.post("/api/v1/scan-url", response_model=ScanResponse)
async def scan_url(request: ScanURLRequest) -> ScanResponse:
    return await analyze_url(request.url)


@app.post("/api/v1/scan-qr", response_model=QRScanResponse)
async def scan_qr(file: UploadFile = File(...)) -> QRScanResponse:
    image_bytes = await file.read()
    try:
        result = QRDecoder.decode_image(image_bytes)
    except Exception:
        return QRScanResponse(
            success=False,
            found=False,
            error="The uploaded file could not be read as an image.",
        )

    if not result["found"]:
        return QRScanResponse(
            success=False,
            found=False,
            error="No QR code could be detected in this image.",
        )

    raw_data = result["raw_data"]
    is_web_url = raw_data.startswith(("http://", "https://"))

    return QRScanResponse(
        success=True,
        found=True,
        type="upi" if result["is_upi"] else "url" if is_web_url else "text",
        payload=raw_data,
        raw_data=raw_data,
        resolved_url=result["resolved_url"] if is_web_url else None,
        is_upi=result["is_upi"],
    )


@app.post("/api/v1/scan-sms", response_model=QRScanResponse)
async def scan_sms(request: ScanSMSRequest) -> QRScanResponse:
    matches = QRDecoder.parse_sms(request.message)

    if not matches:
        return QRScanResponse(
            success=False,
            error="No suspicious link could be detected in this message.",
        )

    return QRScanResponse(
        success=True,
        found=True,
        type="url",
        payload=matches[0]["resolved"],
    )