# Hello API — Production-Grade FastAPI Reference

A minimal "Hello, World!" API that demonstrates the **gold-standard CI/CD pattern** for Python services in 2026.

Designed as a reference implementation for the AI Automation Engineer role: Python + FastAPI + Docker + GitLab CI/CD + DevSecOps, with patterns that extend cleanly to MCP servers and AI agents.

## What's inside

```
hello-api/
├── app/main.py             # FastAPI app with health probes, request IDs, structured logs
├── tests/test_main.py      # pytest suite with coverage
├── Dockerfile              # Multi-stage, non-root, healthcheck baked in
├── .dockerignore           # Build hygiene
├── docker-compose.yml      # Local dev orchestration
├── .gitlab-ci.yml          # 6-stage pipeline: lint → test → security → build → scan → deploy
├── pyproject.toml          # Modern dep management + ruff/mypy/bandit config
├── requirements.txt        # Pinned runtime deps
├── requirements-dev.txt    # Dev + test deps
└── Makefile                # Local dev ergonomics
```

## Quick start

```bash
# Local dev with hot rebuild
make run

# Run tests with coverage
make install && make test

# Build production image
make build
```

Open `http://localhost:8000/` for the API, `http://localhost:8000/docs` for auto-generated OpenAPI docs.

## Endpoints

| Method | Path           | Purpose                                       |
|--------|----------------|-----------------------------------------------|
| GET    | `/`            | Hello world payload                           |
| GET    | `/health/live` | Liveness probe (K8s, ECS, ALB)                |
| GET    | `/health/ready`| Readiness probe (drain on shutdown, dep checks) |
| GET    | `/docs`        | Interactive OpenAPI / Swagger UI              |

## Pipeline stages

1. **lint** — `ruff` (Python) + `hadolint` (Dockerfile). ~30s, fails on style/structure issues.
2. **test** — `pytest` with coverage gate at 80%. JUnit XML uploaded to GitLab MR widget.
3. **security** — `bandit` (Python SAST) + `gitleaks` (committed secrets) + GitLab SAST templates.
4. **build** — Multi-stage Docker build, BuildKit layer caching, pushed to GitLab Container Registry with both `:sha` and `:latest` tags.
5. **scan** — `trivy` image scan, fails on HIGH/CRITICAL CVEs. Report rendered in GitLab Security dashboard.
6. **deploy** — Auto-deploy to staging on merge to `main`. Production requires manual approval (protected env).
