"""Tests for database engine, session lifecycle, and connectivity checks."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.db.session import (
    check_db_connectivity,
    get_db,
    get_engine,
    get_session_factory,
)
from backend.app.main import create_app


def test_get_engine_sqlite_and_memory() -> None:
    """Test engine initialization for SQLite in-memory."""
    engine = get_engine("sqlite:///:memory:")
    assert engine is not None
    assert check_db_connectivity(engine) is True


def test_get_engine_none_url() -> None:
    """Test engine creation returns None when DATABASE_URL is not set."""
    get_engine.cache_clear()
    engine = get_engine("")
    assert engine is None


def test_get_engine_invalid_driver() -> None:
    """Test engine creation handles missing DBAPI driver gracefully."""
    get_engine.cache_clear()
    engine = get_engine("nonexistent_driver://user:pass@localhost/db")
    assert engine is None


def test_get_session_factory_lifecycle() -> None:
    """Test session factory creation and session operations."""
    engine = create_engine("sqlite:///:memory:")
    factory = get_session_factory(engine)
    assert factory is not None

    session: Session = factory()
    assert isinstance(session, Session)
    session.close()


def test_get_session_factory_none() -> None:
    """Test session factory returns None when engine is None."""
    assert get_session_factory(None) is None


def test_get_db_dependency_with_sqlite(monkeypatch) -> None:
    """Test get_db dependency yields a valid session and closes cleanly."""
    sqlite_url = "sqlite:///:memory:"
    get_engine.cache_clear()
    engine = get_engine(sqlite_url)

    # Monkeypatch get_engine in session module
    monkeypatch.setattr("backend.app.db.session.get_engine", lambda *args: engine)

    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    assert isinstance(session, Session)

    # Exhaust generator to test cleanup
    with pytest.raises(StopIteration):
        next(db_gen)


def test_get_db_dependency_when_unconfigured(monkeypatch) -> None:
    """Test get_db dependency yields None when engine is unconfigured."""
    monkeypatch.setattr("backend.app.db.session.get_engine", lambda *args: None)

    db_gen = get_db()
    session = next(db_gen)
    assert session is None

    with pytest.raises(StopIteration):
        next(db_gen)


def test_get_db_dependency_when_factory_is_none(monkeypatch) -> None:
    """Test get_db dependency handles None session factory."""
    mock_engine = create_engine("sqlite:///:memory:")
    monkeypatch.setattr("backend.app.db.session.get_engine", lambda *args: mock_engine)
    monkeypatch.setattr("backend.app.db.session.get_session_factory", lambda *args: None)

    db_gen = get_db()
    session = next(db_gen)
    assert session is None

    with pytest.raises(StopIteration):
        next(db_gen)


def test_check_db_connectivity_failure() -> None:
    """Test connectivity helper returns False for invalid or unreachable database."""
    assert check_db_connectivity(None) is False

    # Broken engine simulation
    bad_engine = create_engine("sqlite:///nonexistent_dir/invalid.db")
    assert check_db_connectivity(bad_engine, timeout_seconds=0.5) is False


def test_health_db_endpoints() -> None:
    """Test /health and /health/db endpoints with database connectivity."""
    settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="sqlite:///:memory:",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    # Test /health includes database status
    r_health = client.get("/health")
    assert r_health.status_code == 200
    data = r_health.json()
    assert data["database"] == "connected"

    # Test /health/db
    r_db = client.get("/health/db")
    assert r_db.status_code == 200
    db_data = r_db.json()
    assert db_data["status"] == "healthy"
    assert db_data["database_connected"] is True
    assert db_data["database_url_configured"] is True


def test_health_db_unconfigured() -> None:
    """Test /health and /health/db endpoints when database is not configured."""
    settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL=None,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["database"] == "not_configured"

    r_db = client.get("/health/db")
    assert r_db.status_code == 200
    db_data = r_db.json()
    assert db_data["status"] == "unconfigured"
    assert db_data["database_connected"] is False
    assert db_data["database_url_configured"] is False
