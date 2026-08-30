"""Pytest fixtures for backend test suite."""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from backend.app.core.config import Settings, get_settings
from backend.app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test configuration settings."""
    return Settings(
        ENVIRONMENT="testing",
        DEBUG=True,
        PROJECT_NAME="ContributorPulse-Test",
        VERSION="0.1.0-test",
        CORS_ORIGINS=["http://testserver"],
        GITHUB_TOKEN="ghp_mock_token_for_testing_1234567890",
        DATABASE_URL="postgresql://test:test@localhost:5432/test_db",
    )


@pytest.fixture
def client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient using configured test settings."""
    app = create_app(settings=test_settings)
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
