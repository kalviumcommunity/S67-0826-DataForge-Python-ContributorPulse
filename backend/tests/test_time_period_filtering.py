"""Tests for time-period filtering and observation window semantics across analytics & exports."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.db.session import get_db
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.user import User


@pytest.fixture
def time_period_client():
    """Create test client with dataset having distinct historic and recent contributors and PRs."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    repo = Repository(
        id=1,
        github_id=2001,
        owner="time-org",
        name="time-repo",
        full_name="time-org/time-repo",
        stars_count=50,
        forks_count=10,
        open_issues_count=5,
        created_at=datetime.now(timezone.utc) - timedelta(days=200),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(repo)

    now = datetime.now(timezone.utc)

    # 1. Historic contributor: first active 150 days ago, not active in last 30d
    u_historic = User(id=1, github_id=3001, login="historic_dev", user_type="User", is_bot=False)
    # 2. Recent contributor: first active 10 days ago (insufficient observation for 30d retention)
    u_recent = User(id=2, github_id=3002, login="recent_dev", user_type="User", is_bot=False)
    # 3. Mature contributor: first active 45 days ago, repeat active 15 days ago (retained 30d)
    u_mature = User(id=3, github_id=3003, login="mature_dev", user_type="User", is_bot=False)
    session.add_all([u_historic, u_recent, u_mature])
    session.commit()

    # Features
    f_historic = ContributorFeature(
        id=1,
        repository_id=1,
        contributor_id=1,
        first_contribution_at=now - timedelta(days=150),
        last_active_at=now - timedelta(days=120),
        first_pr_merged=True,
        is_retained_30d=True,
        is_retained_90d=True,
        total_prs=2,
        merged_prs=2,
        churn_risk_score=0.10,
        churn_risk_level="low",
    )
    f_recent = ContributorFeature(
        id=2,
        repository_id=1,
        contributor_id=2,
        first_contribution_at=now - timedelta(days=10),
        last_active_at=now - timedelta(days=5),
        first_pr_merged=False,
        is_retained_30d=False,  # Not enough time has elapsed
        is_retained_90d=False,
        total_prs=1,
        merged_prs=0,
        churn_risk_score=0.70,
        churn_risk_level="high",
        risk_reason="Slow initial maintainer response (>48h)",
    )
    f_mature = ContributorFeature(
        id=3,
        repository_id=1,
        contributor_id=3,
        first_contribution_at=now - timedelta(days=45),
        last_active_at=now - timedelta(days=15),
        first_pr_merged=True,
        is_retained_30d=True,
        is_retained_90d=False,
        total_prs=3,
        merged_prs=3,
        churn_risk_score=0.20,
        churn_risk_level="low",
    )
    session.add_all([f_historic, f_recent, f_mature])

    # PRs: 1 historic, 1 recent
    pr_historic = PullRequest(
        id=1,
        repository_id=1,
        contributor_id=1,
        github_id=4001,
        number=1,
        title="Old PR",
        state="closed",
        is_merged=True,
        created_at=now - timedelta(days=150),
        merged_at=now - timedelta(days=148),
    )
    pr_recent = PullRequest(
        id=2,
        repository_id=1,
        contributor_id=2,
        github_id=4002,
        number=2,
        title="New PR",
        state="open",
        is_merged=False,
        created_at=now - timedelta(days=10),
    )
    pr_mature = PullRequest(
        id=3,
        repository_id=1,
        contributor_id=3,
        github_id=4003,
        number=3,
        title="Mature PR",
        state="closed",
        is_merged=True,
        created_at=now - timedelta(days=45),
        merged_at=now - timedelta(days=44),
    )
    session.add_all([pr_historic, pr_recent, pr_mature])
    session.commit()
    session.close()

    test_settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="sqlite:///:memory:",
        GITHUB_TOKEN="test_time_period_token",
    )
    app = create_app(settings=test_settings)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_time_period_filtering_kpis(time_period_client: TestClient):
    """Test that specifying period=30d filters KPIs compared to period=all."""
    # Full history: 3 contributors, 3 PRs
    res_all = time_period_client.get("/api/v1/repositories/time-org/time-repo/kpis?period=all")
    assert res_all.status_code == 200
    data_all = res_all.json()["data"]["kpis"]
    assert data_all["merge_rate"]["sample_size"] == 3

    # Last 30 days: only PR 2 and contributor 2, 3 active in last 30d
    res_30d = time_period_client.get("/api/v1/repositories/time-org/time-repo/kpis?period=30d")
    assert res_30d.status_code == 200
    data_30d = res_30d.json()["data"]["kpis"]
    assert data_30d["merge_rate"]["sample_size"] == 1  # only PR 2 created in last 30d
    assert data_30d["merge_rate"]["value"] == 0.0  # unmerged


def test_time_period_filtering_contributors(time_period_client: TestClient):
    """Test that period=30d filters contributor list."""
    res_all = time_period_client.get(
        "/api/v1/repositories/time-org/time-repo/contributors?period=all"
    )
    assert res_all.status_code == 200
    assert len(res_all.json()["data"]["items"]) == 3

    res_30d = time_period_client.get(
        "/api/v1/repositories/time-org/time-repo/contributors?period=30d"
    )
    assert res_30d.status_code == 200
    # Only recent_dev (first active 10d ago) and mature_dev (last active 15d ago)
    logins = [c["login"] for c in res_30d.json()["data"]["items"]]
    assert "historic_dev" not in logins
    assert "recent_dev" in logins


def test_time_period_filtering_exports(time_period_client: TestClient):
    """Test that CSV exports respect the period parameter."""
    res_all = time_period_client.get(
        "/api/v1/repositories/time-org/time-repo/exports/contributors.csv?period=all"
    )
    assert res_all.status_code == 200
    assert "historic_dev" in res_all.text
    assert "recent_dev" in res_all.text

    res_30d = time_period_client.get(
        "/api/v1/repositories/time-org/time-repo/exports/contributors.csv?period=30d"
    )
    assert res_30d.status_code == 200
    assert "historic_dev" not in res_30d.text
    assert "recent_dev" in res_30d.text
