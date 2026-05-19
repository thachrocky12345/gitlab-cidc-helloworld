"""
Hello World API - production-grade FastAPI service.

Demonstrates:
- Structured logging with request IDs
- Health endpoints for Kubernetes/load balancer probes
- Environment-driven configuration
- Async handlers ready for AI workflow integration
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------------------------------------------------------------------------
# Configuration via environment variables (12-factor app)
# ---------------------------------------------------------------------------
APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger("hello-api")


# ---------------------------------------------------------------------------
# Lifespan hook - replaces deprecated on_event("startup"/"shutdown")
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(f"Starting hello-api env={APP_ENV} version={APP_VERSION}")
    yield
    logger.info("Shutting down hello-api")


app = FastAPI(
    title="Hello API",
    version=APP_VERSION,
    description="Production-grade Hello World service",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request ID middleware - critical for tracing in distributed systems
# ---------------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root() -> dict:
    """Public hello-world endpoint."""
    return {
        "message": "Hello, World!",
        "env": APP_ENV,
        "version": APP_VERSION,
    }


@app.get("/health/live")
async def liveness() -> dict:
    """K8s liveness probe - is the process running?"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness() -> dict:
    """K8s readiness probe - can we accept traffic? In real apps,
    check downstream deps (DB, cache, MCP server, etc.) here."""
    return {"status": "ready"}


# ---------------------------------------------------------------------------
# Global exception handler - never leak stack traces in prod
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"unhandled_error path={request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
