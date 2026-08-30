"""Tests for typed environment configuration and secret safety."""

import pytest
from pydantic import ValidationError
from backend.app.core.config import Settings, get_settings


def test_default_settings_instantiation() -> None:
    """Test default settings load without error."""
    settings = Settings(
        ENVIRONMENT="development",
        GITHUB_TOKEN="ghp_dummytoken1234567890",
        DATABASE_URL="postgresql://user:pass@localhost:5432/db",
    )
    assert settings.PROJECT_NAME == "ContributorPulse"
    assert settings.VERSION == "0.1.0"
    assert settings.is_production is False
    assert settings.is_testing is False


def test_cors_origins_parsing() -> None:
    """Test CORS_ORIGINS parses comma-separated string into list."""
    settings = Settings(
        CORS_ORIGINS="http://localhost:3000, http://localhost:8501",
        ENVIRONMENT="development",
    )
    assert settings.CORS_ORIGINS == [
        "http://localhost:3000",
        "http://localhost:8501",
    ]

    # Test empty string returns wildcard default
    empty_cors = Settings(
        CORS_ORIGINS="",
        ENVIRONMENT="development",
    )
    assert empty_cors.CORS_ORIGINS == ["*"]


def test_masked_secrets_safety() -> None:
    """Test secrets are masked and not exposed in repr or safe helpers."""
    token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    db_url = "postgresql://myuser:secretpassword123@db.example.com:5432/pulse"
    settings = Settings(
        GITHUB_TOKEN=token,
        DATABASE_URL=db_url,
        ENVIRONMENT="development",
    )

    masked_tok = settings.masked_github_token()
    assert masked_tok is not None
    assert "secret" not in masked_tok
    assert token not in masked_tok
    assert masked_tok.startswith("ghp_")
    assert masked_tok.endswith("wxyz")

    # Test short token masking
    short_tok_settings = Settings(GITHUB_TOKEN="12345", ENVIRONMENT="development")
    assert short_tok_settings.masked_github_token() == "****"

    # Test None token masking
    none_tok_settings = Settings(GITHUB_TOKEN=None, DATABASE_URL=None, ENVIRONMENT="development")
    assert none_tok_settings.masked_github_token() is None
    assert none_tok_settings.masked_database_url() is None

    masked_db = settings.masked_database_url()
    assert masked_db is not None
    assert "secretpassword123" not in masked_db
    assert ":****@" in masked_db

    repr_str = repr(settings)
    assert "secretpassword123" not in repr_str
    assert token not in repr_str


def test_production_validation_requires_database_url() -> None:
    """Test production environment strictly requires valid remote DATABASE_URL."""
    # Missing database url in production
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL=None,
        )

    # Localhost database url in production
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://postgres:pass@localhost:5432/db",
        )

    # Valid remote database url in production
    prod_settings = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="postgresql://user:password@db.production.internal:5432/pulse",
    )
    assert prod_settings.is_production is True


def test_get_settings_caching() -> None:
    """Test get_settings returns consistent cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
