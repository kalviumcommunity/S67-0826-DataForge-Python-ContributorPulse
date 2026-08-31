"""Deterministic integration tests for FastAPI analytics and contributor endpoints."""

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
def analytics_test_client():
    """Create a test client with in-memory SQLite database and test fixtures."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Populate Test Fixtures
    session = TestingSessionLocal()
    repo = Repository(
        github_id=1001,
        owner="pulse-org",
        name="pulse-api",
        full_name="pulse-org/pulse-api",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    session.add(repo)
    session.flush()

    # User 1: Regular human contributor (retained)
    u1 = User(
        github_id=201,
        login="alice_coder",
        name="Alice Coder",
        avatar_url="https://github.com/alice.png",
        user_type="User",
        is_bot=False,
    )
    # User 2: High risk contributor (unmerged, slow response)
    u2 = User(
        github_id=202,
        login="bob_churn",
        name="Bob Churn",
        avatar_url="https://github.com/bob.png",
        user_type="User",
        is_bot=False,
    )
    # User 3: Maintainer
    u3 = User(
        github_id=203,
        login="charlie_maintainer",
        name="Charlie Maintainer",
        user_type="User",
        is_bot=False,
    )
    session.add_all([u1, u2, u3])
    session.flush()

    t0 = utcnow() - timedelta(days=40)
    t1 = t0 + timedelta(days=10)

    # u1: PR 1 merged, PR 2 open
    pr1 = PullRequest(
        github_id=301,
        repository_id=repo.id,
        contributor_id=u1.id,
        number=1,
        title="feat: first pr",
        state="closed",
        is_merged=True,
        merged_at=t0 + timedelta(hours=6),
        created_at=t0,
    )
    pr2 = PullRequest(
        github_id=302,
        repository_id=repo.id,
        contributor_id=u1.id,
        number=2,
        title="fix: follow up pr",
        state="open",
        created_at=t1,
    )
    # u2: PR 3 closed unmerged
    pr3 = PullRequest(
        github_id=303,
        repository_id=repo.id,
        contributor_id=u2.id,
        number=3,
        title="feat: unmerged pr",
        state="closed",
        is_merged=False,
        created_at=t0,
    )
    session.add_all([pr1, pr2, pr3])
    session.flush()

    # Review by u3 on pr1
    rev1 = Review(
        github_id=401,
        pull_request_id=pr1.id,
        contributor_id=u3.id,
        state="APPROVED",
        submitted_at=t0 + timedelta(hours=3),
    )
    # Comment by u3 on pr1
    com1 = Comment(
        github_id=501,
        repository_id=repo.id,
        pull_request_id=pr1.id,
        contributor_id=u3.id,
        body="LGTM",
        comment_type="pull_request",
        created_at=t0 + timedelta(hours=1),
    )
    session.add_all([rev1, com1])
    session.commit()

    # Run analytics engine to compute features & KPIs
    analytics = AnalyticsService(db=session, repository_id=repo.id)
    analytics.run_pipeline()
    session.close()

    # App setup with overridden DB dependency
    test_settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="sqlite:///:memory:",
        GITHUB_TOKEN="test_token_1234567890",
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
# 1. Summary & KPI Tests
# ------------------------------------------------------------------------------


def test_get_repository_summary_success(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/summary returns valid overview."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/summary")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["status"] == "success"
    summary = data["data"]
    assert summary["full_name"] == "pulse-org/pulse-api"
    assert summary["total_contributors"] >= 2
    assert 0.0 <= summary["health_score"] <= 100.0
    assert summary["merge_rate"] == pytest.approx(33.3, abs=0.1)


def test_get_repository_kpis_success(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/kpis returns all metrics with sample sizes."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/kpis")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert "kpis" in data
    assert "retention_rate_30d" in data["kpis"]
    assert data["kpis"]["merge_rate"]["unit"] == "%"
    assert data["kpis"]["merge_rate"]["sample_size"] == 3


def test_get_unknown_repository_404(analytics_test_client: TestClient) -> None:
    """Test 404 response when querying an unknown repository."""
    resp = analytics_test_client.get("/api/v1/repositories/nonexistent/repo/summary")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    err = resp.json()
    assert err["status"] == "error"
    assert err["error_code"] == "NOT_FOUND"


# ------------------------------------------------------------------------------
# 2. Contributor List & Filter Tests
# ------------------------------------------------------------------------------


def test_get_repository_contributors_paginated(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/contributors pagination & metadata."""
    resp = analytics_test_client.get(
        "/api/v1/repositories/pulse-org/pulse-api/contributors?page=1&per_page=1"
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["pagination"]["current_page"] == 1
    assert data["pagination"]["per_page"] == 1
    assert data["pagination"]["total_records"] >= 2
    assert data["pagination"]["has_next"] is True


def test_get_repository_contributors_filtered(analytics_test_client: TestClient) -> None:
    """Test filtering contributors by search and churn_risk_level."""
    resp = analytics_test_client.get(
        "/api/v1/repositories/pulse-org/pulse-api/contributors?search=alice"
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["login"] == "alice_coder"


# ------------------------------------------------------------------------------
# 3. Funnel, Distribution, Timeline & Stats
# ------------------------------------------------------------------------------


def test_get_retention_funnel(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/funnel returns structured stages."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/funnel")
    assert resp.status_code == status.HTTP_200_OK
    stages = resp.json()["data"]["stages"]
    assert len(stages) == 5
    assert stages[0]["stage"] == "Initial Contribution"
    assert stages[0]["conversion_rate"] == 100.0


def test_get_response_distribution(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/response-distribution."""
    resp = analytics_test_client.get(
        "/api/v1/repositories/pulse-org/pulse-api/response-distribution"
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert len(data["buckets"]) == 6
    assert data["total_evaluated_prs"] >= 2


def test_get_review_timeline(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/review-timeline."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/review-timeline")
    assert resp.status_code == status.HTTP_200_OK
    timeline = resp.json()["data"]["timeline"]
    assert len(timeline) >= 1
    assert "period" in timeline[0]


def test_get_merge_stats(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/merge-stats."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/merge-stats")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["total_prs"] == 3
    assert data["merged_prs"] == 1
    assert data["closed_unmerged_prs"] == 1
    assert data["open_prs"] == 1


# ------------------------------------------------------------------------------
# 4. Correlations, High-Risk & Comparisons
# ------------------------------------------------------------------------------


def test_get_correlation_data(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/correlations."""
    resp = analytics_test_client.get("/api/v1/repositories/pulse-org/pulse-api/correlations")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert data["sample_size"] >= 2
    assert len(data["features"]) >= 2
    assert "churn_risk_score" in data["features"][0]


def test_get_high_risk_contributors(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo}/high-risk-contributors."""
    resp = analytics_test_client.get(
        "/api/v1/repositories/pulse-org/pulse-api/high-risk-contributors"
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert "high_risk_count" in data
    assert isinstance(data["items"], list)


def test_compare_repositories_success(analytics_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/compare with valid repository list."""
    resp = analytics_test_client.get("/api/v1/repositories/compare?repos=pulse-org/pulse-api")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()["data"]
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["full_name"] == "pulse-org/pulse-api"


def test_compare_repositories_invalid_filter_422(analytics_test_client: TestClient) -> None:
    """Test 422 response when invalid repository format is passed."""
    resp = analytics_test_client.get("/api/v1/repositories/compare?repos=invalid-format")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err = resp.json()
    assert err["status"] == "error"
    assert err["error_code"] == "VALIDATION_ERROR"
