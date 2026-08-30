"""SQLAlchemy declarative base class and common timestamp mixin."""

from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Compatible BigInteger type that autoincrements correctly in SQLite as well as PostgreSQL
BigIntPK = BigInteger().with_variant(Integer, "sqlite")
BigIntFK = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> datetime:
    """Return current UTC timestamp with timezone."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM domain models."""
    pass


class TimestampMixin:
    """Mixin that provides created_at and updated_at UTC timestamp columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
