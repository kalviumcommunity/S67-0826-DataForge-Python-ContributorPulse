"""Tests for deterministic duplicate removal and duplicate statistics reporting."""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from backend.app.models.base import Base
from backend.app.models.commit import Commit
from backend.app.models.repository import Repository
from backend.app.models.user import User
from backend.app.processing.pipeline import DataCleaningPipeline


@pytest.fixture
def clean_db_session():
    """Create in-memory SQLite database session for cleaning tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    repo = Repository(
        id=1,
        github_id=1001,
        owner="dedup-org",
        name="dedup-repo",
        full_name="dedup-org/dedup-repo",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(repo)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


def test_deduplication_removes_persisted_duplicate_users(clean_db_session):
    """Test that existing duplicate persisted users (case variations) are deleted, leaving one canonical record."""
    now = datetime.now(timezone.utc)
    u1 = User(
        id=1,
        github_id=5001,
        login="alice",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    u2 = User(
        id=2,
        github_id=5002,
        login="ALICE",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    u3 = User(
        id=3,
        github_id=5003,
        login="Alice",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    clean_db_session.add_all([u1, u2, u3])
    clean_db_session.commit()

    assert clean_db_session.scalar(select(func.count(User.id))) == 3

    pipeline = DataCleaningPipeline(db=clean_db_session, repository_id=1)
    stats = pipeline.run()

    # Verify only 1 canonical user remains in DB
    remaining_users = clean_db_session.scalars(select(User)).all()
    assert len(remaining_users) == 1
    assert remaining_users[0].id == 1
    assert remaining_users[0].login == "alice"

    # Verify statistics counts
    user_stats = stats.dataset_stats["users"]
    assert user_stats["input"] == 3
    assert user_stats["output"] == 1
    assert user_stats["duplicates_detected"] == 2
    assert user_stats["duplicates_removed"] == 2
    assert user_stats["duplicates_retained"] == 1


def test_deduplication_removes_persisted_duplicate_commits(clean_db_session):
    """Test that duplicate commits (differing casing) are deduplicated, retaining the canonical lowercase SHA."""
    now = datetime.now(timezone.utc)
    u = User(
        id=1,
        github_id=5001,
        login="charlie",
        user_type="User",
        is_bot=False,
        created_at=now,
        updated_at=now,
    )
    clean_db_session.add(u)
    clean_db_session.commit()

    c1 = Commit(
        id=1,
        sha="deadbeef123",
        repository_id=1,
        contributor_id=1,
        message="commit 1",
        authored_at=now,
        committed_at=now,
    )
    c2 = Commit(
        id=2,
        sha="DEADBEEF123",
        repository_id=1,
        contributor_id=1,
        message="commit 1 duplicate",
        authored_at=now,
        committed_at=now,
    )
    clean_db_session.add_all([c1, c2])
    clean_db_session.commit()

    pipeline = DataCleaningPipeline(db=clean_db_session, repository_id=1)
    stats = pipeline.run()
    assert stats.dataset_stats["commits"]["duplicates_detected"] == 1
    assert stats.dataset_stats["commits"]["duplicates_removed"] == 1
    assert stats.dataset_stats["commits"]["duplicates_retained"] == 1

    remaining_commits = clean_db_session.scalars(select(Commit)).all()
    assert len(remaining_commits) == 1
    assert remaining_commits[0].sha == "deadbeef123"
