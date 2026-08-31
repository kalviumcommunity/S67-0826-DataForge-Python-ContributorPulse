"""Analysis run tracking domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK, utcnow

if TYPE_CHECKING:
    from backend.app.models.contributor_feature import ContributorFeature
    from backend.app.models.ingestion_error import IngestionError
    from backend.app.models.repository import Repository


class AnalysisRun(Base):
    """SQLAlchemy model tracking ingestion and analysis execution runs."""

    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    repository_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PENDING", nullable=False, index=True
    )  # PENDING, RUNNING, COMPLETED, FAILED
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Ingestion Stats
    total_prs_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_commits_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_issues_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_contributors_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="analysis_runs")
    contributor_features: Mapped[List["ContributorFeature"]] = relationship(
        "ContributorFeature", back_populates="analysis_run"
    )
    ingestion_errors: Mapped[List["IngestionError"]] = relationship(
        "IngestionError", back_populates="analysis_run", cascade="all, delete-orphan"
    )
