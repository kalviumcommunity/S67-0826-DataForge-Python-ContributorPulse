"""Database engine, session management, and connectivity utilities."""

import logging
from functools import lru_cache
from typing import Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import Settings, get_settings

logger = logging.getLogger("contributor_pulse.database")


@lru_cache()
def get_engine(database_url: Optional[str] = None) -> Optional[Engine]:
    """
    Create and cache a SQLAlchemy database engine.

    Args:
        database_url: Optional explicit connection URL. If None, uses settings.DATABASE_URL.

    Returns:
        Engine or None: Configured SQLAlchemy Engine instance if URL is provided and valid.
    """
    url = database_url or get_settings().DATABASE_URL
    if not url:
        logger.warning("DATABASE_URL is not configured; engine initialization skipped.")
        return None

    try:
        # SQLite connection configuration vs PostgreSQL connection pooling
        if url.startswith("sqlite"):
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                echo=False,
            )

        return create_engine(
            url,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            echo=False,
        )
    except Exception as exc:
        logger.warning("Failed to initialize database engine for URL: %s", exc)
        return None


def get_session_factory(engine: Optional[Engine] = None) -> Optional[sessionmaker]:
    """
    Create a sessionmaker factory bound to the provided or default engine.

    Args:
        engine: Optional Engine instance.

    Returns:
        sessionmaker or None: Session factory instance.
    """
    target_engine = engine or get_engine()
    if target_engine is None:
        return None
    return sessionmaker(autocommit=False, autoflush=False, bind=target_engine)


def get_db() -> Generator[Optional[Session], None, None]:
    """
    FastAPI dependency that provides a transactional database session.

    Yields:
        Session: Active SQLAlchemy session.
    """
    engine = get_engine()
    if engine is None:
        yield None
        return

    factory = get_session_factory(engine)
    if factory is None:
        yield None
        return

    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


def check_db_connectivity(engine: Optional[Engine] = None, timeout_seconds: float = 3.0) -> bool:
    """
    Test database connection by executing a lightweight query.

    Args:
        engine: Optional Engine instance to test.
        timeout_seconds: Maximum query execution timeout.

    Returns:
        bool: True if connection succeeded, False otherwise.
    """
    target_engine = engine or get_engine()
    if target_engine is None:
        return False

    try:
        with target_engine.connect() as connection:
            connection.execution_options(timeout=timeout_seconds).execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Unexpected error during database check: %s", exc)
        return False
