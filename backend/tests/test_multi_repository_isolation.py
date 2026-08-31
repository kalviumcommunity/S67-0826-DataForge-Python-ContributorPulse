"""Tests proving strict multi-tenant repository data isolation with overlapping contributors and PR numbers."""

from datetime import datetime, timezone

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
def multi_repo_client():
    """Create test client with 2 distinct repositories and overlapping contributors/PR numbers."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    now = datetime.now(timezone.utc)

    # Repository 1
    repo1 = Repository(
        id=1,
        github_id=1001,
        owner="org-alpha",
        name="project-one",
        full_name="org-alpha/project-one",
        stars_count=100,
        forks_count=20,
        open_issues_count=2,
        created_at=now,
        updated_at=now,
    )
    # Repository 2
    repo2 = Repository(
        id=2,
        github_id=1002,
        owner="org-beta",
        name="project-two",
        full_name="org-beta/project-two",
        stars_count=200,
        forks_count=40,
        open_issues_count=4,
        created_at=now,
        updated_at=now,
    )
    session.add_all([repo1, repo2])

    # Shared Contributor who contributes to both repos
    u_shared = User(
        id=1,
        github_id=5001,
        login="shared_alice",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    # Repo 1 only contributor
    u_repo1 = User(
        id=2,
        github_id=5002,
        login="alpha_bob",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    # Repo 2 only contributor
    u_repo2 = User(
        id=3,
        github_id=5003,
        login="beta_charlie",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    session.add_all([u_shared, u_repo1, u_repo2])
    session.commit()

    # Features for Repo 1
    f1_shared = ContributorFeature(
        id=1,
        repository_id=1,
        contributor_id=1,
        first_contribution_at=now,
        first_pr_merged=True,
        total_prs=5,
        merged_prs=5,
        churn_risk_score=0.10,
        churn_risk_level="low",
    )
    f1_bob = ContributorFeature(
        id=2,
        repository_id=1,
        contributor_id=2,
        first_contribution_at=now,
        first_pr_merged=False,
        total_prs=1,
        merged_prs=0,
        churn_risk_score=0.80,
        churn_risk_level="high",
    )
    # Features for Repo 2
    f2_shared = ContributorFeature(
        id=3,
        repository_id=2,
        contributor_id=1,
        first_contribution_at=now,
        first_pr_merged=False,
        total_prs=1,
        merged_prs=0,
        churn_risk_score=0.75,
        churn_risk_level="high",
    )
    f2_charlie = ContributorFeature(
        id=4,
        repository_id=2,
        contributor_id=3,
        first_contribution_at=now,
        first_pr_merged=True,
        total_prs=10,
        merged_prs=10,
        churn_risk_score=0.05,
        churn_risk_level="low",
    )
    session.add_all([f1_shared, f1_bob, f2_shared, f2_charlie])

    # PR #1 in Repo 1 vs PR #1 in Repo 2 (identical PR number 1 in both repos)
    pr_r1_1 = PullRequest(
        id=1,
        repository_id=1,
        contributor_id=1,
        github_id=9001,
        number=1,
        title="Repo 1 PR #1",
        state="closed",
        is_merged=True,
        created_at=now,
        updated_at=now,
    )
    pr_r2_1 = PullRequest(
        id=2,
        repository_id=2,
        contributor_id=3,
        github_id=9002,
        number=1,
        title="Repo 2 PR #1",
        state="open",
        is_merged=False,
        created_at=now,
        updated_at=now,
    )
    session.add_all([pr_r1_1, pr_r2_1])
    session.commit()
    session.close()

    test_settings = Settings(
        ENVIRONMENT="testing",
        DATABASE_URL="sqlite:///:memory:",
        GITHUB_TOKEN="test_multi_repo_token",
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


def test_contributor_list_isolation(multi_repo_client: TestClient):
    """Test that contributors list for repo 1 never includes repo 2-only contributors and vice versa."""
    res1 = multi_repo_client.get("/api/v1/repositories/org-alpha/project-one/contributors")
    assert res1.status_code == 200
    logins1 = {item["login"] for item in res1.json()["data"]["items"]}
    assert "alpha_bob" in logins1
    assert "shared_alice" in logins1
    assert "beta_charlie" not in logins1

    res2 = multi_repo_client.get("/api/v1/repositories/org-beta/project-two/contributors")
    assert res2.status_code == 200
    logins2 = {item["login"] for item in res2.json()["data"]["items"]}
    assert "beta_charlie" in logins2
    assert "shared_alice" in logins2
    assert "alpha_bob" not in logins2


def test_merge_stats_isolation(multi_repo_client: TestClient):
    """Test PR merge stats for repo 1 (1 merged PR, merge_rate=100%) vs repo 2 (1 open PR, merge_rate=0%)."""
    res1 = multi_repo_client.get("/api/v1/repositories/org-alpha/project-one/merge-stats")
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["total_prs"] == 1
    assert data1["merged_prs"] == 1
    assert data1["merge_rate"] == 100.0

    res2 = multi_repo_client.get("/api/v1/repositories/org-beta/project-two/merge-stats")
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["total_prs"] == 1
    assert data2["merged_prs"] == 0
    assert data2["merge_rate"] == 0.0


def test_high_risk_contributors_isolation(multi_repo_client: TestClient):
    """Test high risk list for repo 1 contains alpha_bob (0.80) while repo 2 contains shared_alice (0.75)."""
    res1 = multi_repo_client.get(
        "/api/v1/repositories/org-alpha/project-one/high-risk-contributors"
    )
    assert res1.status_code == 200
    items1 = res1.json()["data"]["items"]
    assert len(items1) == 1
    assert items1[0]["login"] == "alpha_bob"

    res2 = multi_repo_client.get("/api/v1/repositories/org-beta/project-two/high-risk-contributors")
    assert res2.status_code == 200
    items2 = res2.json()["data"]["items"]
    assert len(items2) == 1
    assert items2[0]["login"] == "shared_alice"
