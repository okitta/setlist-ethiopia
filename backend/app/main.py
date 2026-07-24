"""FastAPI application wiring."""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.routers import artists, attendance, performances, public_api, reports, setlist

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("app")

app = FastAPI(
    title="Setlist Ethiopia API",
    version=__version__,
    summary="A community archive of live music performances in Ethiopia.",
)

# The React dev server and preview deployments call the API from another origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Attach a request id and emit a structured access log for observability."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        extra={
            "context": {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            }
        },
    )
    return response


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "environment": settings.environment, "version": __version__}


@app.get("/features", tags=["ops"])
def features() -> dict:
    """Expose active feature flags so the frontend can adapt its UI."""
    return {
        "attendance": settings.feature_attendance,
        "add_song": settings.feature_add_song,
        "public_api": settings.feature_public_api,
    }


app.include_router(artists.router)
app.include_router(performances.router)
app.include_router(setlist.router)
app.include_router(attendance.router)
app.include_router(reports.router)
app.include_router(public_api.router)


# Normalise our detail dicts into a consistent {code, message} error envelope.
from fastapi.exceptions import HTTPException as _HTTPException  # noqa: E402


@app.exception_handler(_HTTPException)
async def http_exception_handler(request: Request, exc: _HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code, content={"code": "error", "message": str(detail)}
    )
