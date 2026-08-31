"""End-to-end database integration test for data cleaning, validation, and persistence."""

import os

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
from backend.app.processing.pipeline import DataCleaningPipeline


@pytest.fixture
def clean_db_session():
    """Create a clean database session for end-to-end pipeline testing."""
    db_url = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_e2e_cleaning_pipeline_persistence_and_bot_preservation(clean_db_session: Session) -> None:
    """
    End-to-end integration test proving:
    1. Cleaned records are durably persisted in database tables.
    2. Raw bot records are intentionally preserved with is_bot=True.
    3. Missing values and fallbacks are imputed and traceable via statistics.
    4. Invalid records are quarantined and logged to ingestion_errors.
    5. Re-running the pipeline is idempotent and maintains data integrity.
    """
    # --------------------------------------------------------------------------
    # 1. Populate Raw Fixtures
    # --------------------------------------------------------------------------
    repo = Repository(
        github_id=987654,
        owner="pulse-org",
        name="pulse-analytics",
        full_name="pulse-org/pulse-analytics",
        default_branch="main",
        stars_count=50,
        forks_count=10,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    clean_db_session.add(repo)
    clean_db_session.flush()

    # Raw Users: human user with whitespace, bot user, and invalid user
    human_user = User(
        github_id=1001,
        login="  contributor_jane  ",
        name="  Jane Doe  ",
        user_type="User",
        is_bot=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    bot_user = User(
        github_id=1002,
        login="github-actions[bot]",
        name="GitHub Actions Bot",
        user_type="Bot",
        is_bot=False,  # Raw flag un-normalized
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    invalid_user = User(
        github_id=1003,
        login="",  # Invalid blank login
        user_type="User",
        is_bot=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    clean_db_session.add_all([human_user, bot_user, invalid_user])

    # Raw PRs: valid PR with un-normalized state/whitespace, PR with missing title & negative additions
    pr1 = PullRequest(
        github_id=2001,
        repository_id=repo.id,
        contributor_id=human_user.id,
        number=1,
        title="  feat: add contributor retention pipeline  ",
        body="Initial PR for retention",
        state="OPEN",
        additions=150,
        deletions=20,
        created_at=utcnow(),
    )
    pr2 = PullRequest(
        github_id=2002,
        repository_id=repo.id,
        contributor_id=human_user.id,
        number=2,
        title="   ",  # Missing title
        body=None,
        state="CLOSED",
        additions=-50,  # Negative value to clamp
        created_at=utcnow(),
    )
    clean_db_session.add_all([pr1, pr2])
    clean_db_session.flush()

    # Raw Review
    review1 = Review(
        github_id=3001,
        pull_request_id=pr1.id,
        contributor_id=human_user.id,
        state="approved",  # Un-normalized casing
        body="  Looks great to me!  ",
        submitted_at=utcnow(),
    )
    clean_db_session.add(review1)

    # Raw Issue
    issue1 = Issue(
        github_id=4001,
        repository_id=repo.id,
        contributor_id=human_user.id,
        number=10,
        title="   ",  # Missing title
        state="OPEN",
        created_at=utcnow(),
    )
    clean_db_session.add(issue1)

    # Raw Comment
    comment1 = Comment(
        github_id=5001,
        repository_id=repo.id,
        contributor_id=human_user.id,
        pull_request_id=pr1.id,
        body="   ",  # Blank body
        comment_type="issue",
        created_at=utcnow(),
    )
    clean_db_session.add(comment1)

    # Raw Commits: 1 valid, 1 invalid sha
    commit1 = Commit(
        repository_id=repo.id,
        contributor_id=human_user.id,
        sha="1234567890abcdef1234567890abcdef12345678",
        message="  clean commit message  ",
        authored_at=utcnow(),
        committed_at=utcnow(),
        additions=100,
        deletions=10,
    )
    commit_invalid = Commit(
        repository_id=repo.id,
        contributor_id=human_user.id,
        sha="invalid-non-hex-sha!",
        message="broken commit",
        authored_at=utcnow(),
        committed_at=utcnow(),
    )
    clean_db_session.add_all([commit1, commit_invalid])
    clean_db_session.commit()

    # --------------------------------------------------------------------------
    # 2. Execute Cleaning Pipeline
    # --------------------------------------------------------------------------
    pipeline = DataCleaningPipeline(
        db=clean_db_session,
        repository_id=repo.id,
        analysis_run_id=99,
    )
    stats = pipeline.run()

    # --------------------------------------------------------------------------
    # 3. Verify Processing Statistics
    # --------------------------------------------------------------------------
    assert stats.input_count > 0
    assert stats.output_count > 0
    assert stats.invalid_count >= 2  # invalid_user and commit_invalid
    assert stats.missing_values_handled_count >= 3  # pr2 title, issue1 title, comment1 body

    # --------------------------------------------------------------------------
    # 4. Verify Database Persistence of Cleaned Data
    # --------------------------------------------------------------------------
    # Check Human User
    clean_db_session.refresh(human_user)
    assert human_user.login == "contributor_jane"
    assert human_user.name == "Jane Doe"
    assert human_user.is_bot is False

    # Check Bot User is PRESERVED and flagged as bot
    clean_db_session.refresh(bot_user)
    assert bot_user.login == "github-actions[bot]"
    assert bot_user.is_bot is True
    assert bot_user.user_type == "Bot"

    # Check Pull Requests
    clean_db_session.refresh(pr1)
    clean_db_session.refresh(pr2)
    assert pr1.title == "feat: add contributor retention pipeline"
    assert pr1.state == "open"
    assert pr2.title == "(No title)"  # Imputed
    assert pr2.state == "closed"
    assert pr2.additions == 0  # Clamped

    # Check Review
    clean_db_session.refresh(review1)
    assert review1.state == "APPROVED"
    assert review1.body == "Looks great to me!"

    # Check Issue
    clean_db_session.refresh(issue1)
    assert issue1.title == "(No title)"
    assert issue1.state == "open"

    # Check Comment
    clean_db_session.refresh(comment1)
    assert comment1.body == "(empty comment)"

    # Check Commit
    clean_db_session.refresh(commit1)
    assert commit1.message == "clean commit message"

    # Check Quarantined Ingestion Errors
    quarantine_errors = clean_db_session.scalars(
        select(IngestionError).where(
            (IngestionError.repository_id == repo.id)
            & (IngestionError.stage == "cleaning_validation")
        )
    ).all()
    assert len(quarantine_errors) >= 2
    stages = [e.entity_type for e in quarantine_errors]
    assert "user" in stages
    assert "commit" in stages

    # --------------------------------------------------------------------------
    # 5. Verify Idempotent Rerun
    # --------------------------------------------------------------------------
    pipeline_rerun = DataCleaningPipeline(
        db=clean_db_session,
        repository_id=repo.id,
        analysis_run_id=99,
    )
    rerun_stats = pipeline_rerun.run()
    assert rerun_stats.output_count == stats.output_count
    assert pr1.title == "feat: add contributor retention pipeline"
    assert bot_user.is_bot is True
