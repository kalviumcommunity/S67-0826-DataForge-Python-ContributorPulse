"""Unit tests for IngestionService and idempotent persistence."""

from datetime import datetime, timezone
import httpx
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.integrations.exceptions import GitHubNotFoundError
from backend.app.integrations.github import GitHubClient
from backend.app.models.analysis_run import AnalysisRun
from backend.app.models.base import Base
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.ingestion_error import IngestionError
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.services.ingestion import IngestionService, parse_datetime


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for ingestion testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def create_mock_github_client(fail_reviews: bool = False, not_found: bool = False) -> GitHubClient:
    """Helper to instantiate GitHubClient with deterministic mocked endpoints."""
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if not_found:
            return httpx.Response(404, json={"message": "Not Found"})

        if path == "/repos/octocat/Hello-World":
            return httpx.Response(200, json={
                "id": 1296269,
                "name": "Hello-World",
                "full_name": "octocat/Hello-World",
                "owner": {"login": "octocat", "id": 583231},
                "description": "My first repo",
                "stargazers_count": 2500,
                "forks_count": 1200,
                "open_issues_count": 15,
                "language": "Python",
                "default_branch": "main",
                "private": False,
                "fork": False,
                "pushed_at": "2026-08-25T12:00:00Z",
            })
        elif path.endswith("/contributors"):
            return httpx.Response(200, json=[
                {
                    "id": 583231,
                    "login": "octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/583231",
                    "html_url": "https://github.com/octocat",
                    "type": "User",
                },
                {
                    "id": 999999,
                    "login": "contributor1",
                    "avatar_url": "https://avatars.githubusercontent.com/u/999999",
                    "html_url": "https://github.com/contributor1",
                    "type": "User",
                }
            ])
        elif path.endswith("/pulls"):
            return httpx.Response(200, json=[
                {
                    "id": 1001,
                    "number": 1,
                    "title": "Add initial onboarding guide",
                    "body": "Welcome new contributors",
                    "state": "closed",
                    "draft": False,
                    "merged": True,
                    "merged_at": "2026-08-20T10:00:00Z",
                    "created_at": "2026-08-19T08:00:00Z",
                    "closed_at": "2026-08-20T10:00:00Z",
                    "author_association": "FIRST_TIME_CONTRIBUTOR",
                    "user": {"id": 999999, "login": "contributor1", "type": "User"},
                    "additions": 150,
                    "deletions": 10,
                    "changed_files": 3,
                }
            ])
        elif "/reviews" in path:
            if fail_reviews:
                return httpx.Response(500, json={"message": "Review fetch error"})
            return httpx.Response(200, json=[
                {
                    "id": 2001,
                    "state": "APPROVED",
                    "body": "Great first PR!",
                    "submitted_at": "2026-08-19T14:00:00Z",
                    "user": {"id": 583231, "login": "octocat", "type": "User"},
                }
            ])
        elif path.endswith("/issues"):
            return httpx.Response(200, json=[
                {
                    "id": 3001,
                    "number": 2,
                    "title": "Improve documentation for onboarding",
                    "body": "Clarify setup steps",
                    "state": "open",
                    "created_at": "2026-08-21T09:00:00Z",
                    "user": {"id": 999999, "login": "contributor1", "type": "User"},
                    "comments": 2,
                }
            ])
        elif path.endswith("/comments"):
            return httpx.Response(200, json=[
                {
                    "id": 4001,
                    "body": "I will take a look at this issue.",
                    "created_at": "2026-08-21T11:00:00Z",
                    "issue_url": "https://api.github.com/repos/octocat/Hello-World/issues/2",
                    "user": {"id": 583231, "login": "octocat", "type": "User"},
                }
            ])
        elif path.endswith("/commits"):
            return httpx.Response(200, json=[
                {
                    "sha": "a1b2c3d4e5f6",
                    "commit": {
                        "message": "docs: add getting started section",
                        "author": {"name": "contributor1", "date": "2026-08-19T07:30:00Z"},
                        "committer": {"name": "contributor1", "date": "2026-08-19T07:30:00Z"},
                    },
                    "author": {"id": 999999, "login": "contributor1", "type": "User"},
                    "stats": {"additions": 150, "deletions": 10, "total": 160},
                }
            ])
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)
    return GitHubClient(client=http_client)


def test_parse_datetime_helper() -> None:
    """Test parse_datetime handles None, invalid, and ISO-8601 strings."""
    assert parse_datetime(None) is None
    assert parse_datetime("invalid-date") is None

    dt = parse_datetime("2026-08-30T12:00:00Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo == timezone.utc


def test_full_ingestion_success(db_session: Session) -> None:
    """Test full repository ingestion correctly persists all domain entities."""
    github_client = create_mock_github_client()
    service = IngestionService(db=db_session, github_client=github_client)

    run = service.ingest_repository("octocat", "Hello-World")
    assert run.status == "COMPLETED"
    assert run.total_prs_ingested == 1
    assert run.total_commits_ingested == 1
    assert run.total_issues_ingested == 1
    assert run.total_contributors_ingested == 1

    # Verify repository record
    repo = db_session.scalars(select(Repository).where(Repository.full_name == "octocat/Hello-World")).first()
    assert repo is not None
    assert repo.stars_count == 2500
    assert repo.primary_language == "Python"

    # Verify users
    users = db_session.scalars(select(User)).all()
    assert len(users) == 2

    # Verify PR and Review
    pr = db_session.scalars(select(PullRequest).where(PullRequest.repository_id == repo.id)).first()
    assert pr is not None
    assert pr.is_first_time_contributor is True
    assert pr.is_merged is True
    assert len(pr.reviews) == 1
    assert pr.reviews[0].state == "APPROVED"

    # Verify Issue
    issue = db_session.scalars(select(Issue).where(Issue.repository_id == repo.id)).first()
    assert issue is not None
    assert issue.title == "Improve documentation for onboarding"

    # Verify Comment
    comment = db_session.scalars(select(Comment).where(Comment.repository_id == repo.id)).first()
    assert comment is not None
    assert "take a look" in comment.body

    # Verify Commit
    commit = db_session.scalars(select(Commit).where(Commit.repository_id == repo.id)).first()
    assert commit is not None
    assert commit.sha == "a1b2c3d4e5f6"


def test_ingestion_idempotence_no_duplicates(db_session: Session) -> None:
    """Test repeated ingestion updates records without creating duplicates."""
    github_client = create_mock_github_client()
    service = IngestionService(db=db_session, github_client=github_client)

    # First run
    run1 = service.ingest_repository("octocat", "Hello-World")
    assert run1.status == "COMPLETED"

    prs_count_1 = db_session.scalar(select(func.count(PullRequest.id)))
    commits_count_1 = db_session.scalar(select(func.count(Commit.id)))
    issues_count_1 = db_session.scalar(select(func.count(Issue.id)))
    users_count_1 = db_session.scalar(select(func.count(User.id)))

    # Second run for same repository
    run2 = service.ingest_repository("octocat", "Hello-World")
    assert run2.status == "COMPLETED"

    prs_count_2 = db_session.scalar(select(func.count(PullRequest.id)))
    commits_count_2 = db_session.scalar(select(func.count(Commit.id)))
    issues_count_2 = db_session.scalar(select(func.count(Issue.id)))
    users_count_2 = db_session.scalar(select(func.count(User.id)))

    assert prs_count_1 == prs_count_2 == 1
    assert commits_count_1 == commits_count_2 == 1
    assert issues_count_1 == issues_count_2 == 1
    assert users_count_1 == users_count_2 == 2


def test_partial_failure_logs_ingestion_errors(db_session: Session) -> None:
    """Test non-fatal sub-dataset failure logs to ingestion_errors and marks run partially completed."""
    github_client = create_mock_github_client(fail_reviews=True)
    service = IngestionService(db=db_session, github_client=github_client)

    run = service.ingest_repository("octocat", "Hello-World")
    assert run.status == "PARTIALLY_COMPLETED"

    # Verify ingestion error was recorded
    errors = db_session.scalars(select(IngestionError).where(IngestionError.analysis_run_id == run.id)).all()
    assert len(errors) >= 1
    assert errors[0].stage == "reviews"


def test_repository_not_found(db_session: Session) -> None:
    """Test non-existent repository raises GitHubNotFoundError."""
    github_client = create_mock_github_client(not_found=True)
    service = IngestionService(db=db_session, github_client=github_client)

    with pytest.raises(GitHubNotFoundError):
        service.ingest_repository("nonexistent", "repo")
