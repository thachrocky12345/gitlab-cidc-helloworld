# syntax=docker/dockerfile:1.7
# ============================================================================
# STAGE 1: builder - install dependencies into a virtualenv
# ============================================================================
# Use a specific patch version (not :latest) for reproducibility.
# "-slim" gives us ~40MB vs ~900MB for the full Python image.
FROM python:3.12.7-slim AS builder

# Compile-time env vars: smaller, faster, no .pyc clutter, no buffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build deps only in this stage; they never reach the final image
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY requirements first - maximizes Docker layer cache hits.
# If source changes but deps don't, this layer is reused (huge speedup).
COPY requirements.txt .

# Create a virtualenv we can copy whole into the runtime image
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir -r requirements.txt

# ============================================================================
# STAGE 2: runtime - minimal image with just the app and its deps
# ============================================================================
FROM python:3.12.7-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production

# Create non-root user BEFORE copying files so ownership is correct.
# Running as root inside a container is a well-known security smell;
# CIS Docker benchmark explicitly flags it.
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --no-create-home appuser

# Install only what runtime needs: curl for the HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy the prebuilt virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code (owned by non-root user)
COPY --chown=appuser:appgroup app/ ./app/

USER appuser

EXPOSE 8000

# HEALTHCHECK gives Docker/K8s/ECS a way to know the container is healthy.
# K8s also has its own probes, but this is the floor.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Gunicorn (process manager) + Uvicorn workers (ASGI) = production standard.
# --workers: rule of thumb is (2 * CPU) + 1, but tune for your workload.
# Don't use `uvicorn --reload` in prod — that's dev-only.
CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "30"]
