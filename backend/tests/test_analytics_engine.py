"""Deterministic unit and integration tests for retention features and KPI engine."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.analytics.engine import (
    AnalyticsService,
    ContributorFeatureEngine,
    RepositoryKPIEngine,
)
from backend.app.models.base import Base, utcnow
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.review import Review
from backend.app.models.user import User


@pytest.fixture
def db_session():
    """Isolated SQLite in-memory database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_contributor_features_full_onboarding_velocity(db_session: Session) -> None:
    """Test contributor feature calculations with known timestamps, review time, response time, and merge time."""
    repo = Repository(
        github_id=1001,
        owner="pulse-org",
        name="pulse-core",
        full_name="pulse-org/pulse-core",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    author = User(github_id=201, login="alice_dev", name="Alice Dev", user_type="User", is_bot=False)
    reviewer = User(github_id=202, login="bob_maintainer", name="Bob Maintainer", user_type="User", is_bot=False)
    db_session.add_all([author, reviewer])
    db_session.flush()

    base_time = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    response_time = base_time + timedelta(hours=2)      # 7,200 seconds
    review_time = base_time + timedelta(hours=4)        # 14,400 seconds
    merge_time = base_time + timedelta(hours=10)        # 36,000 seconds

    # First PR created at base_time, merged at merge_time
    pr1 = PullRequest(
        github_id=301,
        repository_id=repo.id,
        contributor_id=author.id,
        number=1,
        title="feat: core feature",
        state="closed",
        is_merged=True,
        merged_at=merge_time,
        created_at=base_time,
    )
    db_session.add(pr1)
    db_session.flush()

    # Review by reviewer at review_time
    rev1 = Review(
        github_id=401,
        pull_request_id=pr1.id,
        contributor_id=reviewer.id,
        state="APPROVED",
        submitted_at=review_time,
    )
    # Comment by reviewer at response_time
    com1 = Comment(
        github_id=501,
        repository_id=repo.id,
        contributor_id=reviewer.id,
        pull_request_id=pr1.id,
        body="LGTM!",
        comment_type="pull_request",
        created_at=response_time,
    )
    db_session.add_all([rev1, com1])

    # Second PR 15 days later (triggers 30-day retention)
    second_pr_time = base_time + timedelta(days=15)
    pr2 = PullRequest(
        github_id=302,
        repository_id=repo.id,
        contributor_id=author.id,
        number=2,
        title="fix: bugfix",
        state="open",
        created_at=second_pr_time,
    )
    db_session.add(pr2)
    db_session.commit()

    # Calculate features
    engine = ContributorFeatureEngine(db=db_session, repository_id=repo.id)
    cf = engine.calculate_for_contributor(author)

    assert cf.first_contribution_at.replace(tzinfo=timezone.utc) == base_time
    assert cf.first_pr_id == pr1.id
    assert cf.first_pr_merged is True
    assert cf.first_response_time_seconds == pytest.approx(7200.0)
    assert cf.first_pr_review_duration_seconds == pytest.approx(14400.0)
    assert cf.first_pr_merge_duration_seconds == pytest.approx(36000.0)
    assert cf.total_prs == 2
    assert cf.merged_prs == 1
    assert cf.is_retained_30d is True
    assert cf.is_retained_90d is False
    assert cf.retention_status == "retained"
    assert cf.experience_level == "repeat"
    assert cf.churn_risk_level == "low"


def test_contributor_without_merges_or_reviews(db_session: Session) -> None:
    """Test feature calculations when PR is unmerged and has no reviews."""
    repo = Repository(
        github_id=1002,
        owner="pulse-org",
        name="pulse-drafts",
        full_name="pulse-org/pulse-drafts",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    author = User(github_id=203, login="lonely_coder", user_type="User", is_bot=False)
    db_session.add(author)
    db_session.flush()

    # PR closed unmerged 70 days ago
    old_time = utcnow() - timedelta(days=70)
    pr = PullRequest(
        github_id=303,
        repository_id=repo.id,
        contributor_id=author.id,
        number=1,
        title="feat: abandoned experiment",
        state="closed",
        is_merged=False,
        created_at=old_time,
    )
    db_session.add(pr)
    db_session.commit()

    engine = ContributorFeatureEngine(db=db_session, repository_id=repo.id)
    cf = engine.calculate_for_contributor(author)

    assert cf.first_pr_merged is False
    assert cf.first_pr_review_duration_seconds is None
    assert cf.first_pr_merge_duration_seconds is None
    assert cf.first_response_time_seconds is None
    assert cf.total_prs == 1
    assert cf.merged_prs == 0
    assert cf.is_retained_30d is False
    assert cf.is_retained_90d is False
    assert cf.retention_status == "churned"
    assert cf.churn_risk_level == "high"
    assert "closed unmerged" in cf.risk_reason.lower()


def test_repository_kpis_and_health_score_bounds(db_session: Session) -> None:
    """Test repository KPI calculations, sample size metadata, and health score bounds (0-100)."""
    repo = Repository(
        github_id=1003,
        owner="pulse-org",
        name="pulse-kpis",
        full_name="pulse-org/pulse-kpis",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    u1 = User(github_id=204, login="dev1", user_type="User", is_bot=False)
    u2 = User(github_id=205, login="dev2", user_type="User", is_bot=False)
    db_session.add_all([u1, u2])
    db_session.flush()

    t0 = utcnow() - timedelta(days=45)
    t1 = t0 + timedelta(days=10)

    # u1: 2 PRs, 1 merged
    pr1 = PullRequest(
        github_id=304,
        repository_id=repo.id,
        contributor_id=u1.id,
        number=1,
        title="feat: u1 first pr",
        state="closed",
        is_merged=True,
        created_at=t0,
        merged_at=t0 + timedelta(hours=4),
    )
    pr2 = PullRequest(
        github_id=305,
        repository_id=repo.id,
        contributor_id=u1.id,
        number=2,
        title="fix: u1 second pr",
        state="open",
        is_merged=False,
        created_at=t1,
    )
    # u2: 1 PR open
    pr3 = PullRequest(
        github_id=306,
        repository_id=repo.id,
        contributor_id=u2.id,
        number=3,
        title="feat: u2 initial pr",
        state="open",
        is_merged=False,
        created_at=t0,
    )
    db_session.add_all([pr1, pr2, pr3])
    db_session.commit()

    # Run full analytics
    analytics = AnalyticsService(db=db_session, repository_id=repo.id)
    summary = analytics.run_pipeline()

    kpis = summary["kpis"]
    assert kpis["total_contributors"] == 2
    assert kpis["merge_rate"] == pytest.approx(33.3, abs=0.1)  # 1 of 3 merged
    assert 0.0 <= kpis["health_score"] <= 100.0
    assert "sample_sizes" in kpis
    assert kpis["sample_sizes"]["total_prs"] == 3


def test_empty_repository_division_by_zero_safety(db_session: Session) -> None:
    """Test KPI calculations against an empty repository with 0 PRs and 0 contributors."""
    repo = Repository(
        github_id=1004,
        owner="pulse-org",
        name="pulse-empty",
        full_name="pulse-org/pulse-empty",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.commit()

    kpi_engine = RepositoryKPIEngine(db=db_session, repository_id=repo.id)
    kpis = kpi_engine.calculate_kpis()

    assert kpis["total_contributors"] == 0
    assert kpis["retention_rate_30d"] is None
    assert kpis["retention_rate_90d"] is None
    assert kpis["merge_rate"] == 0.0
    assert kpis["avg_review_time_hours"] is None
    assert kpis["avg_response_time_hours"] is None
    assert 0.0 <= kpis["health_score"] <= 100.0


def test_idempotent_feature_calculation_without_duplicate_rows(db_session: Session) -> None:
    """Test running AnalyticsService multiple times updates the existing row without creating duplicates."""
    repo = Repository(
        github_id=1005,
        owner="pulse-org",
        name="pulse-idempotent",
        full_name="pulse-org/pulse-idempotent",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    user = User(github_id=206, login="repeat_coder", user_type="User", is_bot=False)
    db_session.add(user)
    db_session.flush()

    pr = PullRequest(
        github_id=307,
        repository_id=repo.id,
        contributor_id=user.id,
        number=1,
        title="feat: idempotent test pr",
        state="open",
        created_at=utcnow(),
    )
    db_session.add(pr)
    db_session.commit()

    # First run
    analytics = AnalyticsService(db=db_session, repository_id=repo.id, analysis_run_id=1)
    analytics.run_pipeline()

    count_1 = db_session.scalar(
        select(func.count(ContributorFeature.id)).where(ContributorFeature.repository_id == repo.id)
    )
    assert count_1 == 1

    # Second run
    analytics_2 = AnalyticsService(db=db_session, repository_id=repo.id, analysis_run_id=2)
    analytics_2.run_pipeline()

    count_2 = db_session.scalar(
        select(func.count(ContributorFeature.id)).where(ContributorFeature.repository_id == repo.id)
    )
    assert count_2 == 1
