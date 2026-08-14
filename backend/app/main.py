"""
Agentic AI VAPT Framework — FastAPI Application Entry Point

Sets up:
- Application lifecycle (lifespan)
- CORS middleware
- Structured logging
- All API routers
- Health endpoints
- OpenAPI documentation
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database.session import init_db, close_db
from app.api.routes import (
    health,
    targets,
    runs,
    payloads,
    artifacts,
    telemetry,
    evaluations,
    findings,
    reports,
    experiments,
    dashboard,
    authorizations,
)
from app.observability import configure_logging, configure_otel

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager: startup → yield → shutdown."""
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging()
    logger.info(
        "vapt_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
        db=settings.effective_database_url.split("://")[0],
        llm_enabled=settings.llm_enabled,
    )

    # Initialize database (run migrations if needed)
    await init_db()

    # Configure OpenTelemetry if enabled
    if settings.otel_enabled:
        configure_otel()

    logger.info("vapt_startup_complete", message="VAPT Framework ready")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("vapt_shutdown", message="Shutting down VAPT Framework")
    await close_db()


# ─── Create FastAPI Application ───────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Agentic AI VAPT Framework

**Origin-Aware Behavioral VAPT: A Telemetry-Driven Architecture for Agentic Prompt-Injection Assessment**

This platform assesses agentic AI systems by observing actual behavior, tool calls,
instruction origins, multi-turn state, and downstream actions — not just text classification.

### Key Features

- **4 Attack Pipelines**: Direct injection, Indirect/Artifact injection, Multi-turn Crescendo, Tool-output injection
- **Instruction-Origin Tracking**: Every instruction span is tagged with its source
- **Deterministic Evaluation**: Signal-based evaluation engine with bounded LLM judge
- **AgenticRiskScore**: Multi-factor severity scoring with explainable breakdowns
- **Evidence Bundles**: Immutable, tamper-evident telemetry with hash-chains
- **Attack Graphs**: Automatically built from telemetry
- **Professional Reports**: JSON, HTML, PDF with Llama 3B narrative

### Security Model

By default, all assessments run in a sandboxed mock environment.
Real target mode requires an explicit authorization record.
    """,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
    debug=settings.debug,
)

# ─── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next) -> Response:
    """Add request ID and timing to every request."""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.monotonic()

    response = await call_next(request)

    duration_ms = (time.monotonic() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
        request_id=request_id,
    )

    return response


# ─── Exception Handlers ────────────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": "The requested resource was not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Any) -> JSONResponse:
    logger.error("internal_server_error", path=request.url.path, exc=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred"},
    )


# ─── API Routers ──────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(targets.router, prefix=API_PREFIX, tags=["Targets"])
app.include_router(authorizations.router, prefix=API_PREFIX, tags=["Authorizations"])
app.include_router(runs.router, prefix=API_PREFIX, tags=["Runs"])
app.include_router(payloads.router, prefix=API_PREFIX, tags=["Payloads"])
app.include_router(artifacts.router, prefix=API_PREFIX, tags=["Artifacts"])
app.include_router(telemetry.router, prefix=API_PREFIX, tags=["Telemetry"])
app.include_router(evaluations.router, prefix=API_PREFIX, tags=["Evaluations"])
app.include_router(findings.router, prefix=API_PREFIX, tags=["Findings"])
app.include_router(reports.router, prefix=API_PREFIX, tags=["Reports"])
app.include_router(experiments.router, prefix=API_PREFIX, tags=["Experiments"])
app.include_router(dashboard.router, prefix=API_PREFIX, tags=["Dashboard"])


# ─── Root ─────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs",
        "health": "/api/health",
        "status": "running",
    }
