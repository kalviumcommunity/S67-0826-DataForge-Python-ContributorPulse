"""Ingestion error tracking domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK, utcnow

if TYPE_CHECKING:
    from backend.app.models.analysis_run import AnalysisRun
    from backend.app.models.repository import Repository


class IngestionError(Base):
    """SQLAlchemy model logging pipeline failures and entity ingestion errors."""

    __tablename__ = "ingestion_errors"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_run_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g., "pull_requests", "commits", "features"
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="ingestion_errors")
    analysis_run: Mapped[Optional["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="ingestion_errors"
    )
