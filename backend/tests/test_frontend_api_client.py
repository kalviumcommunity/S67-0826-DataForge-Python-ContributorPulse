"""Deterministic unit tests for Streamlit-to-FastAPI BackendAPIClient."""

import os
import pytest
import httpx

from api_client import (
    APIClientError,
    APIConnectionError,
    APINotFoundError,
    APIRateLimitError,
    APIServerError,
    APITimeoutError,
    APIValidationError,
    BackendAPIClient,
    get_backend_url,
    sanitize_error_message,
)


def test_get_backend_url_default_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test resolution of backend URL from default and environment variables."""
    monkeypatch.delenv("BACKEND_URL", raising=False)
    monkeypatch.delenv("API_URL", raising=False)
    assert get_backend_url() == "http://localhost:8000"

    monkeypatch.setenv("BACKEND_URL", "http://custom-api:9000/")
    assert get_backend_url() == "http://custom-api:9000"


def test_sanitize_error_message() -> None:
    """Test sanitization of GitHub tokens and database URLs in error outputs."""
    raw_token_err = "Failed authentication for token ghp_1234567890abcdef1234567890"
    sanitized = sanitize_error_message(raw_token_err)
    assert "ghp_" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized

    raw_db_err = "Database connection failed at postgresql://postgres:secret_pass@localhost:5432/contributor_pulse"
    sanitized_db = sanitize_error_message(raw_db_err)
    assert "secret_pass" not in sanitized_db
    assert "[REDACTED_DATABASE_URL]" in sanitized_db


def test_trigger_analysis_mock_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful trigger_analysis call with mocked httpx response."""
    mock_payload = {
        "status": "success",
        "data": {
            "run_id": "test-uuid-1234",
            "status": "COMPLETED",
            "total_prs_ingested": 10,
        },
    }

    def mock_request(self, method, url, **kwargs):
        return httpx.Response(200, json=mock_payload, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    res = client.trigger_analysis("test-org", "test-repo")
    assert res["run_id"] == "test-uuid-1234"
    assert res["status"] == "COMPLETED"


def test_get_repository_kpis_mock_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_repository_kpis parses and returns KPI summary."""
    mock_payload = {
        "status": "success",
        "data": {
            "repository_id": 1,
            "health_score": 88.0,
            "kpis": {
                "merge_rate": {"value": 75.0, "unit": "%", "sample_size": 20},
            },
        },
    }

    def mock_request(self, method, url, **kwargs):
        return httpx.Response(200, json=mock_payload, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    kpis = client.get_repository_kpis("test-org", "test-repo")
    assert kpis is not None
    assert kpis["health_score"] == 88.0
    assert kpis["kpis"]["merge_rate"]["value"] == 75.0


def test_404_not_found_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 404 response raises APINotFoundError."""
    def mock_request(self, method, url, **kwargs):
        return httpx.Response(404, json={"status": "error", "message": "Repository not found."}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APINotFoundError) as exc_info:
        client.trigger_analysis("unknown", "repo")
    assert "Repository not found" in exc_info.value.message


def test_422_validation_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 422 response raises APIValidationError."""
    def mock_request(self, method, url, **kwargs):
        return httpx.Response(422, json={"status": "error", "message": "Invalid parameter."}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APIValidationError) as exc_info:
        client.trigger_analysis("", "")
    assert exc_info.value.status_code == 422


def test_429_rate_limit_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 429 response raises APIRateLimitError."""
    def mock_request(self, method, url, **kwargs):
        return httpx.Response(429, json={"status": "error", "message": "Rate limit exceeded."}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APIRateLimitError):
        client.trigger_analysis("test-org", "test-repo")


def test_500_server_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 500/503 response raises APIServerError."""
    def mock_request(self, method, url, **kwargs):
        return httpx.Response(500, json={"status": "error", "message": "Internal error."}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APIServerError):
        client.trigger_analysis("test-org", "test-repo")


def test_timeout_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test httpx.TimeoutException raises APITimeoutError."""
    def mock_request(self, method, url, **kwargs):
        raise httpx.TimeoutException("Connection timed out")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APITimeoutError) as exc_info:
        client.trigger_analysis("test-org", "test-repo")
    assert "timed out" in exc_info.value.message


def test_connection_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test httpx.NetworkError raises APIConnectionError."""
    def mock_request(self, method, url, **kwargs):
        raise httpx.NetworkError("Failed to connect")

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    with pytest.raises(APIConnectionError) as exc_info:
        client.trigger_analysis("test-org", "test-repo")
    assert "Cannot connect" in exc_info.value.message


def test_empty_and_not_found_getters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test helper getters return None when 404 is encountered."""
    def mock_request(self, method, url, **kwargs):
        return httpx.Response(404, json={"status": "error"}, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx.Client, "request", mock_request)

    client = BackendAPIClient(base_url="http://test-server")
    assert client.get_repository("owner", "nonexistent") is None
    assert client.get_repository_summary("owner", "nonexistent") is None
    assert client.get_repository_kpis("owner", "nonexistent") is None
    assert client.get_contributors("owner", "nonexistent") is None
    assert client.get_retention_funnel("owner", "nonexistent") is None
    assert client.get_response_distribution("owner", "nonexistent") is None
    assert client.get_review_timeline("owner", "nonexistent") is None
    assert client.get_merge_stats("owner", "nonexistent") is None
    assert client.get_correlation_data("owner", "nonexistent") is None
    assert client.get_high_risk_contributors("owner", "nonexistent") is None
