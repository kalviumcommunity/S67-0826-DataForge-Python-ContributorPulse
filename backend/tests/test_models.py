"""Unit tests for SQLAlchemy models, relationships, and constraints."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models.base import Base
from backend.app.models.repository import Repository
from backend.app.models.user import User
from backend.app.models.pull_request import PullRequest
from backend.app.models.issue import Issue
from backend.app.models.review import Review
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.analysis_run import AnalysisRun
from backend.app.models.ingestion_error import IngestionError


@pytest.fixture
def db_session():
    """Create in-memory SQLite database and provide isolated session for model testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_schema_table_names(db_session: Session) -> None:
    """Verify that all 10 required domain tables are registered and created."""
    inspector = inspect(db_session.bind)
    tables = inspector.get_table_names()
    expected_tables = {
        "repositories",
        "users",
        "analysis_runs",
        "pull_requests",
        "issues",
        "reviews",
        "commits",
        "comments",
        "contributor_features",
        "ingestion_errors",
    }
    assert expected_tables.issubset(set(tables))


def test_repository_and_user_creation(db_session: Session) -> None:
    """Test creating a repository and user record."""
    repo = Repository(
        github_id=123456,
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        description="My first repo",
        primary_language="Python",
        stars_count=100,
        forks_count=20,
    )
    user = User(
        github_id=98765,
        login="contributor1",
        name="Jane Contributor",
        email="jane@example.com",
    )
    db_session.add_all([repo, user])
    db_session.commit()

    assert repo.id is not None
    assert user.id is not None
    assert repo.full_name == "octocat/Hello-World"
    assert user.login == "contributor1"
    assert repo.created_at is not None
    assert user.created_at is not None


def test_pull_request_relationships(db_session: Session) -> None:
    """Test pull request creation and foreign key relationships with repository and user."""
    repo = Repository(
        github_id=101,
        owner="org",
        name="repo-pr",
        full_name="org/repo-pr",
    )
    user = User(github_id=202, login="pr-author")
    db_session.add_all([repo, user])
    db_session.commit()

    pr = PullRequest(
        github_id=303,
        repository_id=repo.id,
        contributor_id=user.id,
        number=1,
        title="Add initial feature",
        state="open",
        is_first_time_contributor=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(pr)
    db_session.commit()

    assert pr.id is not None
    assert pr.repository.name == "repo-pr"
    assert pr.contributor.login == "pr-author"
    assert repo.pull_requests[0].number == 1


def test_issue_relationships(db_session: Session) -> None:
    """Test issue creation and relationship with user and repository."""
    repo = Repository(github_id=111, owner="org", name="issue-repo", full_name="org/issue-repo")
    user = User(github_id=222, login="issue-creator")
    db_session.add_all([repo, user])
    db_session.commit()

    issue = Issue(
        github_id=333,
        repository_id=repo.id,
        contributor_id=user.id,
        number=10,
        title="Bug in parser",
        state="open",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(issue)
    db_session.commit()

    assert issue.id is not None
    assert repo.issues[0].title == "Bug in parser"


def test_review_and_comment_relationships(db_session: Session) -> None:
    """Test creating review and comments linked to PR and repository."""
    repo = Repository(github_id=121, owner="org", name="rev-repo", full_name="org/rev-repo")
    author = User(github_id=232, login="author-user")
    reviewer = User(github_id=343, login="reviewer-user")
    db_session.add_all([repo, author, reviewer])
    db_session.commit()

    pr = PullRequest(
        github_id=454,
        repository_id=repo.id,
        contributor_id=author.id,
        number=5,
        title="PR for review",
        state="open",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(pr)
    db_session.commit()

    review = Review(
        github_id=565,
        pull_request_id=pr.id,
        contributor_id=reviewer.id,
        state="APPROVED",
        body="Looks great!",
        submitted_at=datetime.now(timezone.utc),
    )
    comment = Comment(
        github_id=676,
        repository_id=repo.id,
        contributor_id=reviewer.id,
        pull_request_id=pr.id,
        comment_type="pull_request",
        body="Thank you for your contribution!",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([review, comment])
    db_session.commit()

    assert len(pr.reviews) == 1
    assert pr.reviews[0].state == "APPROVED"
    assert len(pr.comments) == 1
    assert pr.comments[0].body == "Thank you for your contribution!"


def test_commit_creation(db_session: Session) -> None:
    """Test commit creation and relationship with repository and contributor."""
    repo = Repository(github_id=787, owner="org", name="commit-repo", full_name="org/commit-repo")
    user = User(github_id=898, login="committer")
    db_session.add_all([repo, user])
    db_session.commit()

    commit = Commit(
        repository_id=repo.id,
        contributor_id=user.id,
        sha="abc123def456789",
        message="feat: initial commit",
        authored_at=datetime.now(timezone.utc),
        committed_at=datetime.now(timezone.utc),
        additions=50,
        deletions=2,
        total_changes=52,
    )
    db_session.add(commit)
    db_session.commit()

    assert commit.id is not None
    assert commit.sha == "abc123def456789"
    assert len(repo.commits) == 1


def test_contributor_features_and_analysis_run(db_session: Session) -> None:
    """Test analysis run and contributor retention feature models."""
    repo = Repository(github_id=990, owner="org", name="feature-repo", full_name="org/feature-repo")
    user = User(github_id=991, login="retained-user")
    db_session.add_all([repo, user])
    db_session.commit()

    run = AnalysisRun(
        run_id="run-uuid-1234",
        repository_id=repo.id,
        status="COMPLETED",
        total_prs_ingested=10,
        total_commits_ingested=25,
    )
    db_session.add(run)
    db_session.commit()

    feature = ContributorFeature(
        repository_id=repo.id,
        contributor_id=user.id,
        analysis_run_id=run.id,
        first_contribution_at=datetime.now(timezone.utc),
        first_pr_merged=True,
        total_prs=3,
        merged_prs=3,
        total_commits=10,
        is_first_time_contributor=True,
        is_retained_30d=True,
        retention_status="retained",
        churn_risk_score=0.1,
        churn_risk_level="low",
    )
    db_session.add(feature)
    db_session.commit()

    assert feature.id is not None
    assert feature.retention_status == "retained"
    assert feature.churn_risk_score == 0.1
    assert run.contributor_features[0].id == feature.id


def test_ingestion_error_creation(db_session: Session) -> None:
    """Test ingestion error tracking model."""
    repo = Repository(github_id=999, owner="org", name="err-repo", full_name="org/err-repo")
    db_session.add(repo)
    db_session.commit()

    err = IngestionError(
        repository_id=repo.id,
        stage="commits",
        entity_type="commit",
        entity_identifier="sha_xyz",
        error_message="Rate limit exceeded",
    )
    db_session.add(err)
    db_session.commit()

    assert err.id is not None
    assert err.stage == "commits"
    assert len(repo.ingestion_errors) == 1


def test_unique_constraints(db_session: Session) -> None:
    """Test unique constraints prevent duplicate records."""
    repo1 = Repository(github_id=1001, owner="dup", name="repo", full_name="dup/repo")
    db_session.add(repo1)
    db_session.commit()

    # Attempt duplicate full_name
    repo2 = Repository(github_id=1002, owner="dup", name="repo", full_name="dup/repo")
    db_session.add(repo2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
