"""Comprehensive deterministic tests for data cleaning, validation, and processing pipeline."""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models.base import Base, utcnow
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.ingestion_error import IngestionError
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.processing.cleaners import (
    clean_comment_data,
    clean_commit_data,
    clean_issue_data,
    clean_pull_request_data,
    clean_review_data,
    clean_user_data,
)
from backend.app.processing.normalizers import normalize_text, normalize_timestamp
from backend.app.processing.pipeline import DataCleaningPipeline, ProcessingStatistics


@pytest.fixture
def db_session():
    """Isolated in-memory SQLite database session for pipeline testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ------------------------------------------------------------------------------
# 1. Normalizer Tests
# ------------------------------------------------------------------------------

def test_normalize_text() -> None:
    """Test text normalization rules."""
    assert normalize_text(None) is None
    assert normalize_text("", default="default_val") == "default_val"
    assert normalize_text("   Hello World!  \n\t") == "Hello World!"
    assert normalize_text("Title\x00with null\r\nbytes") == "Titlewith null\nbytes"
    assert normalize_text("   ") is None
    assert normalize_text("   ", default="fallback") == "fallback"


def test_normalize_timestamp() -> None:
    """Test timestamp standardization to UTC."""
    assert normalize_timestamp(None) is None
    assert normalize_timestamp("invalid-date-string") is None
    assert normalize_timestamp("") is None

    # Epoch integer
    dt_epoch = normalize_timestamp(1700000000)
    assert dt_epoch is not None
    assert dt_epoch.tzinfo == timezone.utc

    # Naive datetime
    naive_dt = datetime(2026, 8, 30, 12, 0, 0)
    dt_from_naive = normalize_timestamp(naive_dt)
    assert dt_from_naive.tzinfo == timezone.utc

    # Aware datetime with non-UTC offset
    aware_dt = datetime(2026, 8, 30, 17, 30, 0, tzinfo=timezone.utc)
    assert normalize_timestamp(aware_dt) == aware_dt

    # ISO string with Z
    dt_iso_z = normalize_timestamp("2026-08-30T12:00:00Z")
    assert dt_iso_z.year == 2026
    assert dt_iso_z.tzinfo == timezone.utc

    # ISO string with offset
    dt_iso_offset = normalize_timestamp("2026-08-30T17:30:00+05:30")
    assert dt_iso_offset.tzinfo == timezone.utc
    assert dt_iso_offset.hour == 12  # 17:30 - 5:30 = 12:00 UTC

    # Custom format fallback
    dt_custom = normalize_timestamp("2026-08-30 12:00:00")
    assert dt_custom.year == 2026
    assert dt_custom.tzinfo == timezone.utc


# ------------------------------------------------------------------------------
# 2. Cleaner Tests
# ------------------------------------------------------------------------------

def test_clean_user_data() -> None:
    """Test user cleaning and bot detection."""
    # Valid user
    user_raw = {"id": 100, "login": "  dev_alice  ", "type": "User"}
    cleaned, errors, missing = clean_user_data(user_raw)
    assert not errors
    assert cleaned["login"] == "dev_alice"
    assert cleaned["is_bot"] is False

    # Bot user via login
    bot_raw = {"id": 101, "login": "dependabot[bot]", "type": "Bot"}
    cleaned_bot, errors, _ = clean_user_data(bot_raw)
    assert not errors
    assert cleaned_bot["is_bot"] is True

    # Invalid user ID
    invalid_raw = {"id": -1, "login": "bad_id"}
    cleaned_inv, errors, _ = clean_user_data(invalid_raw)
    assert cleaned_inv is None
    assert len(errors) > 0


def test_clean_pull_request_data() -> None:
    """Test pull request cleaning and missing value strategies."""
    # Valid PR with missing title & negative additions
    pr_raw = {
        "id": 500,
        "number": 10,
        "title": "   ",
        "state": "OPEN",
        "created_at": "2026-08-20T10:00:00Z",
        "merged_at": "2026-08-21T12:00:00Z",
        "additions": -50,
        "author_association": "FIRST_TIME_CONTRIBUTOR",
    }
    cleaned, errors, missing = clean_pull_request_data(pr_raw)
    assert not errors
    assert cleaned["title"] == "(No title)"
    assert cleaned["state"] == "open"
    assert cleaned["is_merged"] is True
    assert cleaned["additions"] == 0
    assert cleaned["is_first_time_contributor"] is True
    assert missing >= 1

    # Invalid PR missing created_at
    pr_inv = {"id": 501, "number": 11}
    cleaned_inv, errors, _ = clean_pull_request_data(pr_inv)
    assert cleaned_inv is None
    assert len(errors) > 0


def test_clean_issue_data() -> None:
    """Test issue cleaning and title fallback."""
    issue_raw = {
        "id": 600,
        "number": 5,
        "title": "  Bug in onboarding flow  ",
        "state": "closed",
        "created_at": "2026-08-20T10:00:00Z",
    }
    cleaned, errors, _ = clean_issue_data(issue_raw)
    assert not errors
    assert cleaned["title"] == "Bug in onboarding flow"
    assert cleaned["state"] == "closed"


def test_clean_review_data() -> None:
    """Test review state standardization."""
    review_raw = {
        "id": 700,
        "state": "approved",
        "submitted_at": "2026-08-20T11:00:00Z",
    }
    cleaned, errors, _ = clean_review_data(review_raw)
    assert not errors
    assert cleaned["state"] == "APPROVED"

    # Unknown review state defaults to COMMENTED
    review_unknown = {
        "id": 701,
        "state": "UNKNOWN_CUSTOM_STATE",
        "submitted_at": "2026-08-20T11:00:00Z",
    }
    cleaned_unk, errors, missing = clean_review_data(review_unknown)
    assert cleaned_unk["state"] == "COMMENTED"
    assert missing >= 1


def test_clean_comment_data() -> None:
    """Test comment body normalization."""
    comment_raw = {
        "id": 800,
        "body": "   ",
        "created_at": "2026-08-20T12:00:00Z",
    }
    cleaned, errors, missing = clean_comment_data(comment_raw)
    assert not errors
    assert cleaned["body"] == "(empty comment)"
    assert missing >= 1


def test_clean_commit_data() -> None:
    """Test commit SHA validation and stats normalization."""
    # Valid commit
    commit_raw = {
        "sha": "a1b2c3d4e5f67890123456789012345678901234",
        "commit": {
            "message": "  feat: add retention metrics  ",
            "author": {"date": "2026-08-20T08:00:00Z"},
        },
        "stats": {"additions": 100, "deletions": 20},
    }
    cleaned, errors, _ = clean_commit_data(commit_raw)
    assert not errors
    assert cleaned["message"] == "feat: add retention metrics"
    assert cleaned["additions"] == 100
    assert cleaned["deletions"] == 20
    assert cleaned["total_changes"] == 120

    # Invalid commit SHA
    commit_inv = {"sha": "not-a-hex-sha-!!!"}
    cleaned_inv, errors, _ = clean_commit_data(commit_inv)
    assert cleaned_inv is None
    assert len(errors) > 0


# ------------------------------------------------------------------------------
# 3. Pipeline Integration Tests
# ------------------------------------------------------------------------------

def test_pipeline_execution_and_statistics(db_session: Session) -> None:
    """Test full DataCleaningPipeline execution, normalization, and error quarantine."""
    # 1. Setup repository
    repo = Repository(
        github_id=123456,
        owner="test-org",
        name="pulse-repo",
        full_name="test-org/pulse-repo",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    # 2. Add raw users (1 valid, 1 invalid with missing login)
    user1 = User(github_id=1, login="  alice  ", created_at=utcnow(), updated_at=utcnow())
    user2 = User(github_id=2, login="", created_at=utcnow(), updated_at=utcnow())
    db_session.add_all([user1, user2])

    # 3. Add raw PRs (1 valid with whitespace, 1 with missing title and negative additions)
    pr1 = PullRequest(
        github_id=101,
        repository_id=repo.id,
        number=1,
        title="  Fix login redirect  ",
        state="OPEN",
        created_at=utcnow(),
    )
    pr2 = PullRequest(
        github_id=102,
        repository_id=repo.id,
        number=2,
        title="   ",
        state="closed",
        additions=-10,
        created_at=utcnow(),
    )
    db_session.add_all([pr1, pr2])

    # 4. Add raw Commits (1 valid, 1 invalid format)
    commit1 = Commit(
        repository_id=repo.id,
        sha="abcdef1234567890",
        message="  init commit  ",
        authored_at=utcnow(),
        committed_at=utcnow(),
    )
    commit_inv = Commit(
        repository_id=repo.id,
        sha="invalid_sha_format!",
        message="broken",
        authored_at=utcnow(),
        committed_at=utcnow(),
    )
    db_session.add_all([commit1, commit_inv])
    db_session.commit()

    # 5. Execute DataCleaningPipeline
    pipeline = DataCleaningPipeline(db=db_session, repository_id=repo.id, analysis_run_id=1)
    stats = pipeline.run()

    # Verify statistics
    assert stats.input_count > 0
    assert stats.output_count > 0
    assert stats.invalid_count >= 2  # user2 and commit_inv are invalid
    assert stats.missing_values_handled_count >= 1  # pr2 title imputed and additions clamped

    # Verify quarantined errors logged to ingestion_errors table
    errors = db_session.scalars(
        select(IngestionError).where(IngestionError.stage == "cleaning_validation")
    ).all()
    assert len(errors) >= 2

    # Verify values normalized in database
    db_session.refresh(user1)
    db_session.refresh(pr1)
    db_session.refresh(pr2)
    db_session.refresh(commit1)
    assert user1.login == "alice"
    assert pr1.title == "Fix login redirect"
    assert pr1.state == "open"
    assert pr2.title == "(No title)"
    assert pr2.additions == 0
    assert commit1.message == "init commit"


def test_pipeline_idempotency(db_session: Session) -> None:
    """Test running DataCleaningPipeline multiple times produces identical clean output."""
    repo = Repository(
        github_id=999,
        owner="idempotent-org",
        name="repo",
        full_name="idempotent-org/repo",
        default_branch="main",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        github_id=888,
        repository_id=repo.id,
        number=1,
        title="  Clean Me  ",
        state="OPEN",
        created_at=utcnow(),
    )
    db_session.add(pr)
    db_session.commit()

    # Run 1
    pipeline1 = DataCleaningPipeline(db=db_session, repository_id=repo.id)
    stats1 = pipeline1.run()

    # Run 2
    pipeline2 = DataCleaningPipeline(db=db_session, repository_id=repo.id)
    stats2 = pipeline2.run()

    assert stats1.output_count == stats2.output_count
    assert pr.title == "Clean Me"
    assert pr.state == "open"
