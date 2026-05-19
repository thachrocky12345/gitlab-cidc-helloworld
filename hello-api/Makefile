.PHONY: help install test lint security build run stop clean

help:
	@echo "Hello API - common commands"
	@echo "  make install   - install dev dependencies"
	@echo "  make test      - run pytest with coverage"
	@echo "  make lint      - ruff + hadolint"
	@echo "  make security  - bandit + gitleaks (requires both installed)"
	@echo "  make build     - build Docker image"
	@echo "  make run       - run via docker-compose"
	@echo "  make stop      - stop docker-compose stack"
	@echo "  make clean     - remove caches and venv"

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements-dev.txt

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && ruff check app/ tests/ && ruff format --check app/ tests/
	docker run --rm -i hadolint/hadolint < Dockerfile

security:
	. .venv/bin/activate && bandit -r app/ --severity-level medium
	gitleaks detect --source .

build:
	docker build -t hello-api:local .

run:
	docker compose up --build

stop:
	docker compose down

clean:
	rm -rf .venv .cache .pytest_cache .ruff_cache .mypy_cache __pycache__
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
