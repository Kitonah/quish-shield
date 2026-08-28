from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.orchestrator import analyze_url
from backend.schemas import ScanResponse, ScanURLRequest


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