"""Tests for hello-api. Run with: pytest -v --cov=app"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_root_returns_hello(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Hello, World!"
    assert "env" in body
    assert "version" in body


def test_liveness_probe(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_probe(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_request_id_header_propagates(client: TestClient) -> None:
    """Custom X-Request-ID should be echoed back for distributed tracing."""
    response = client.get("/", headers={"X-Request-ID": "test-trace-123"})
    assert response.headers["X-Request-ID"] == "test-trace-123"


def test_request_id_header_generated_when_missing(client: TestClient) -> None:
    response = client.get("/")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
