"""Tests for health check endpoints and standardized error handlers."""

import pytest
from fastapi import APIRouter, HTTPException, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from backend.app.core.config import Settings
from backend.app.main import create_app


def test_health_endpoint(client: TestClient) -> None:
    """Test that the /health endpoint returns 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "ContributorPulse Backend"
    assert data["version"] == "0.1.0-test"
    assert data["environment"] == "testing"
    assert "timestamp" in data


def test_api_v1_health_endpoint(client: TestClient) -> None:
    """Test that the /api/v1/health route returns 200 and matches top-level /health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0-test"


def test_root_endpoint(client: TestClient) -> None:
    """Test that the root endpoint returns welcome info and docs links."""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "ContributorPulse" in data["message"]
    assert data["docs_url"] == "/docs"
    assert data["health_url"] == "/health"
    assert data["version"] == "0.1.0-test"


def test_not_found_error_format(client: TestClient) -> None:
    """Test that a 404 error returns standard ErrorResponse envelope."""
    response = client.get("/api/v1/non-existent-endpoint-xyz")
    assert response.status_code == 404

    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "NOT_FOUND"
    assert "Not Found" in data["message"]
    assert "timestamp" in data


def test_http_exception_statuses() -> None:
    """Test standard HTTP status code translations in error envelope."""
    test_router = APIRouter()

    @test_router.get("/test-401")
    def trigger_401():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    @test_router.get("/test-403")
    def trigger_403():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden resource")

    @test_router.get("/test-400")
    def trigger_400():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request payload")

    @test_router.get("/test-500")
    def trigger_500():
        raise RuntimeError("Unexpected boom!")

    class SampleModel(BaseModel):
        count: int = Field(..., gt=0)

    @test_router.post("/test-validation")
    def trigger_val(payload: SampleModel):
        return payload

    app = create_app(Settings(ENVIRONMENT="testing"))
    app.include_router(test_router)
    custom_client = TestClient(app, raise_server_exceptions=False)

    # 401
    r_401 = custom_client.get("/test-401")
    assert r_401.status_code == 401
    assert r_401.json()["error_code"] == "UNAUTHORIZED"

    # 403
    r_403 = custom_client.get("/test-403")
    assert r_403.status_code == 403
    assert r_403.json()["error_code"] == "FORBIDDEN"

    # 400
    r_400 = custom_client.get("/test-400")
    assert r_400.status_code == 400
    assert r_400.json()["error_code"] == "BAD_REQUEST"

    # 422 Validation
    r_val = custom_client.post("/test-validation", json={"count": -5})
    assert r_val.status_code == 422
    assert r_val.json()["error_code"] == "VALIDATION_ERROR"
    assert len(r_val.json()["details"]) > 0

    # 500 Unhandled
    r_500 = custom_client.get("/test-500")
    assert r_500.status_code == 500
    assert r_500.json()["error_code"] == "INTERNAL_SERVER_ERROR"
