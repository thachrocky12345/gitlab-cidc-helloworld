# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

The actual project lives in the `hello-api/` subdirectory; the repo root only contains a stub `README.md`. All commands below assume you are inside `hello-api/`.

```
hello-api/
├── app/main.py             FastAPI app (single module)
├── tests/test_main.py      pytest suite
├── Dockerfile              Multi-stage build, non-root runtime user
├── docker-compose.yml      Local dev orchestration
├── .gitlab-ci.yml          6-stage pipeline
├── SAST.gitlab-ci.yml      GitLab SAST template (vendored)
├── Secret-Detection.gitlab-ci.yml  GitLab secret detection template (vendored)
├── pyproject.toml          Tool config (ruff/mypy/pytest/bandit)
├── requirements.txt        Pinned runtime deps
├── requirements-dev.txt    Dev + test deps
└── Makefile                Local dev wrapper
```

## Common commands

All targets are defined in `hello-api/Makefile` and assume a POSIX shell (`. .venv/bin/activate`). On Windows use Git Bash / WSL, or run the underlying commands directly with `.venv\Scripts\activate`.

| Command | Purpose |
|---|---|
| `make install` | Create `.venv` and install `requirements-dev.txt` |
| `make test` | Run pytest with coverage (config from `pyproject.toml`: `-v --strict-markers --cov=app --cov-report=term-missing --cov-report=xml`) |
| `make lint` | `ruff check` + `ruff format --check` on `app/ tests/`, then `hadolint Dockerfile` via Docker |
| `make security` | `bandit -r app/ --severity-level medium` + `gitleaks detect --source .` |
| `make build` | `docker build -t hello-api:local .` |
| `make run` | `docker compose up --build` (serves on `http://localhost:8000`) |
| `make stop` | `docker compose down` |
| `make clean` | Remove `.venv` and all Python/tool caches |

Single test: `pytest tests/test_main.py::test_root_returns_hello -v` (after activating `.venv`).

Coverage gate in CI is **80%** (`coverage report --fail-under=80`), enforced in `test:pytest` job. Keep this in mind when adding code without tests.

## Architecture

Single-file FastAPI service (`app/main.py`) intentionally kept flat. The notable production-oriented patterns to preserve when extending:

- **12-factor config**: `APP_ENV`, `APP_VERSION`, `LOG_LEVEL` are read from env at import time. Tests don't override these; add new config the same way.
- **Lifespan context manager** (`@asynccontextmanager`) replaces the deprecated `on_event("startup"/"shutdown")`. Use this hook for downstream dependency setup (DB pools, MCP clients, etc.).
- **Request ID middleware** echoes `X-Request-ID` for distributed tracing — generated as a UUID4 when missing. Any new middleware should preserve this contract.
- **Health probe split**: `/health/live` (process alive) vs `/health/ready` (can accept traffic). Readiness is the right place to add dependency checks; liveness must stay trivial or K8s will restart-loop the pod.
- **Global exception handler** returns a generic `{"detail": "Internal server error"}` with 500. Never replace this with a handler that leaks stack traces or internal paths.
- **JSON-formatted log lines** via `logging.basicConfig` format string — keep new logs structured (don't switch to plain text) so they parse cleanly in log aggregators.

Production process model is **Gunicorn + Uvicorn workers** (see `Dockerfile` CMD). The compose stack uses the same image. Do not run `uvicorn --reload` in any image intended for non-local use.

## Docker / image

`Dockerfile` is a two-stage build:
1. **builder**: installs `build-essential` and pip-installs `requirements.txt` into `/opt/venv`.
2. **runtime**: `python:3.12.7-slim`, copies the prebuilt venv, runs as non-root `appuser:appgroup` (uid/gid 1001), installs only `curl` for the `HEALTHCHECK`.

When changing dependencies, edit `requirements.txt` (runtime) or `requirements-dev.txt` (test/lint only — must never reach the runtime image). The runtime stage deliberately does not install dev deps.

## GitLab CI/CD pipeline

Defined in `hello-api/.gitlab-ci.yml`. Six sequential stages, jobs parallel within a stage:

1. **lint** — `lint:ruff` (uses `.python-base` anchor) + `lint:hadolint` (Dockerfile linting in a separate image).
2. **test** — `test:pytest` produces `coverage.xml` (Cobertura) and `report.xml` (JUnit); both are uploaded as GitLab reports for the MR widget. Coverage regex parses `(?i)total.*? <pct>%` from terminal output.
3. **security** — Includes GitLab templates `Jobs/SAST.gitlab-ci.yml` and `Jobs/Secret-Detection.gitlab-ci.yml`, plus custom `security:bandit` and `security:gitleaks` jobs. `bandit` runs twice: once to dump JSON (`|| true`), once with `--severity-level medium` to enforce a gate.
4. **build** — `build:image` uses `docker:27.3.1-dind` with `DOCKER_TLS_CERTDIR=/certs`, logs in to `$CI_REGISTRY`, builds with BuildKit cache from `:latest`, and pushes both `:$CI_COMMIT_SHORT_SHA` and `:latest`. Runs only on default branch or MR events.
5. **scan** — `scan:trivy` pulls the just-built image, produces a GitLab-formatted container scanning report, and fails on HIGH/CRITICAL CVEs. Uses `GIT_STRATEGY: none` (no source checkout needed).
6. **deploy** — `deploy:staging` auto-runs on default branch; `deploy:production` requires `when: manual` and `needs: ["deploy:staging"]`. Both jobs currently only `echo` — real deploy logic (Ansible/Helm/ArgoCD/ECS) is a TODO marked in comments.

Shared infra:
- `.python-cache` anchor caches `.cache/pip` and `.venv/` keyed on `requirements*.txt`.
- `.python-base` extends image `python:3.12.7-slim` and installs `requirements-dev.txt` in `before_script`.
- `DOCKER_BUILDKIT=1` is set globally to speed up image builds.

`SAST.gitlab-ci.yml` and `Secret-Detection.gitlab-ci.yml` at the project root are vendored copies of GitLab templates — the active pipeline pulls them via `include: template:`, so the vendored files are reference only.

## Code style

- `ruff` with line length 100, target `py312`, lint rules `["E", "F", "I", "N", "W", "B", "C4", "SIM", "UP"]` (see `[tool.ruff.lint]` in `pyproject.toml`). Both `ruff check` AND `ruff format --check` must pass.
- `mypy` is configured (`strict = true`, `python_version = 3.12`) but not yet wired into CI — running it locally is optional but recommended for new code.
- `bandit` excludes `tests` and `.venv`.
