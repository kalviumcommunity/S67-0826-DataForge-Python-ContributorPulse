"""Tests for Alembic migrations up, down, and schema integrity."""

import os
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture
def migration_config():
    """Create a temporary SQLite database file and configured Alembic Config."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    db_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = db_url

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    yield alembic_cfg, db_url, db_path

    # Cleanup temp db file
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass


def test_alembic_upgrade_downgrade_cycle(migration_config) -> None:
    """
    Test full migration lifecycle:
    1. Upgrade to head from empty database
    2. Verify all 10 tables exist
    3. Downgrade to base
    4. Verify all tables removed cleanly in reverse order
    5. Upgrade to head again
    """
    alembic_cfg, db_url, _ = migration_config
    engine = create_engine(db_url)

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

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 2. Inspect created tables
    inspector = inspect(engine)
    created_tables = set(inspector.get_table_names())
    assert expected_tables.issubset(created_tables)
    assert "alembic_version" in created_tables

    # 3. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 4. Inspect tables after downgrade
    inspector = inspect(engine)
    remaining_tables = set(inspector.get_table_names()) - {"alembic_version"}
    assert len(remaining_tables) == 0

    # 5. Upgrade to head again to ensure re-migration is deterministic
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    recreated_tables = set(inspector.get_table_names())
    assert expected_tables.issubset(recreated_tables)
