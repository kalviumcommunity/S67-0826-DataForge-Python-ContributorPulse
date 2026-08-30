"""Deterministic unit and integration tests for export endpoints and readiness probe."""

import csv
import io
import json
from datetime import timedelta
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.analytics.engine import AnalyticsService
from backend.app.core.config import Settings
from backend.app.db.session import get_db
from backend.app.main import create_app
from backend.app.models.base import Base, utcnow
from backend.app.models.comment import Comment
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.review import Review
from backend.app.models.user import User


@pytest.fixture
def exports_test_client():
    """Create test client with in-memory SQLite fixtures."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    repo = Repository(
        github_id=2001,
        owner="export-org",
        name="pulse-export",
        full_name="export-org/pulse-export",
        default_branch="main",
        stars_count=120,
        forks_count=45,
        open_issues_count=8,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(repo)
    session.flush()

    u1 = User(
        github_id=301,
        login="alice_exporter",
        name="Alice Exporter",
        user_type="User",
        is_bot=False,
    )
    session.add(u1)
    session.flush()

    t0 = utcnow() - timedelta(days=20)
    pr1 = PullRequest(
        github_id=401,
        repository_id=repo.id,
        contributor_id=u1.id,
        number=1,
        title="feat: export pr",
        state="closed",
        is_merged=True,
        merged_at=t0 + timedelta(hours=4),
        created_at=t0,
    )
    session.add(pr1)
    session.flush()

    rev1 = Review(
        github_id=501,
        pull_request_id=pr1.id,
        contributor_id=u1.id,
        state="APPROVED",
        submitted_at=t0 + timedelta(hours=2),
    )
    session.add(rev1)
    session.commit()

    analytics = AnalyticsService(db=session, repository_id=repo.id)
    analytics.run_pipeline()
    session.close()

    test_settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="sqlite:///:memory:",
        GITHUB_TOKEN="ghp_test_token_1234567890",
    )
    app = create_app(settings=test_settings)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


# ------------------------------------------------------------------------------
# 1. Contributor CSV Export Tests
# ------------------------------------------------------------------------------

def test_export_contributors_csv_success(exports_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/exports/contributors.csv returns valid CSV."""
    resp = exports_test_client.get("/api/v1/repositories/export-org/pulse-export/exports/contributors.csv")
    assert resp.status_code == status.HTTP_200_OK
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment; filename=" in resp.headers["content-disposition"]
    assert "contributor_pulse_export-org_pulse-export_contributors.csv" in resp.headers["content-disposition"]

    csv_reader = csv.reader(io.StringIO(resp.text))
    rows = list(csv_reader)
    assert len(rows) >= 2  # Header + at least 1 record
    headers = rows[0]
    assert "login" in headers
    assert "churn_risk_score" in headers
    assert "experience_level" in headers
    assert "risk_reason" in headers
    assert rows[1][0] == "alice_exporter"


# ------------------------------------------------------------------------------
# 2. KPIs CSV Export Tests
# ------------------------------------------------------------------------------

def test_export_kpis_csv_success(exports_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/exports/kpis.csv returns structured KPIs."""
    resp = exports_test_client.get("/api/v1/repositories/export-org/pulse-export/exports/kpis.csv")
    assert resp.status_code == status.HTTP_200_OK
    assert "text/csv" in resp.headers["content-type"]
    assert "contributor_pulse_export-org_pulse-export_kpis.csv" in resp.headers["content-disposition"]

    csv_reader = csv.reader(io.StringIO(resp.text))
    rows = list(csv_reader)
    assert len(rows) >= 5
    headers = rows[0]
    assert headers == ["metric_key", "metric_name", "value", "unit", "sample_size", "description"]


# ------------------------------------------------------------------------------
# 3. JSON Intelligence Report Tests
# ------------------------------------------------------------------------------

def test_export_report_json_success(exports_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/exports/report.json returns complete report."""
    resp = exports_test_client.get("/api/v1/repositories/export-org/pulse-export/exports/report.json")
    assert resp.status_code == status.HTTP_200_OK
    assert "application/json" in resp.headers["content-type"]
    data = resp.json()
    assert "report_title" in data
    assert "generated_at" in data
    assert data["repository"]["full_name"] == "export-org/pulse-export"
    assert "health_score" in data
    assert "kpis" in data


# ------------------------------------------------------------------------------
# 4. HTML Report Tests
# ------------------------------------------------------------------------------

def test_export_report_html_success(exports_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/exports/report.html returns styled HTML."""
    resp = exports_test_client.get("/api/v1/repositories/export-org/pulse-export/exports/report.html")
    assert resp.status_code == status.HTTP_200_OK
    assert "text/html" in resp.headers["content-type"]
    assert "export-org/pulse-export" in resp.text
    assert "<!DOCTYPE html>" in resp.text
    assert "Health Score:" in resp.text


# ------------------------------------------------------------------------------
# 5. Error & 404 Tests
# ------------------------------------------------------------------------------

def test_export_unknown_repository_404(exports_test_client: TestClient) -> None:
    """Test 404 status when exporting non-existent repository."""
    resp = exports_test_client.get("/api/v1/repositories/unknown/repo/exports/report.json")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ------------------------------------------------------------------------------
# 6. Readiness Probe Tests
# ------------------------------------------------------------------------------

def test_health_readiness_probe_success(exports_test_client: TestClient) -> None:
    """Test GET /health/ready returns 200 ready status."""
    resp = exports_test_client.get("/health/ready")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "ready"
    assert data["database_connected"] is True


def test_no_secrets_in_exports(exports_test_client: TestClient) -> None:
    """Verify that export payloads do not contain secret tokens or passwords."""
    for path in [
        "/api/v1/repositories/export-org/pulse-export/exports/contributors.csv",
        "/api/v1/repositories/export-org/pulse-export/exports/kpis.csv",
        "/api/v1/repositories/export-org/pulse-export/exports/report.json",
        "/api/v1/repositories/export-org/pulse-export/exports/report.html",
    ]:
        resp = exports_test_client.get(path)
        assert "ghp_" not in resp.text
        assert "postgrespassword" not in resp.text
