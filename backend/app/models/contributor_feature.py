"""Contributor features and retention metrics domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK, utcnow

if TYPE_CHECKING:
    from backend.app.models.analysis_run import AnalysisRun
    from backend.app.models.pull_request import PullRequest
    from backend.app.models.repository import Repository
    from backend.app.models.user import User


class ContributorFeature(Base):
    """
    SQLAlchemy model storing calculated onboarding, retention features, and risk signals
    for a contributor in a given repository (Supports Appendix B, FR-07, FR-09, FR-11, FR-13, FR-14, FR-15, FR-17).
    """

    __tablename__ = "contributor_features"
    __table_args__ = (
        UniqueConstraint("repository_id", "contributor_id", name="uq_contributor_features_repo_contributor"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contributor_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    analysis_run_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # First-time contributor onboarding journey metrics (Appendix B)
    first_contribution_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    first_pr_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("pull_requests.id", ondelete="SET NULL"), nullable=True
    )
    first_pr_merged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_pr_review_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_pr_merge_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_response_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Activity Aggregations
    total_prs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    merged_prs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_commits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_issues: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Retention Signals & Risk Scoring
    is_first_time_contributor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_retained_30d: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_retained_60d: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_retained_90d: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    retention_status: Mapped[str] = mapped_column(
        String(50), default="onboarding", nullable=False, index=True
    )  # onboarding, retained, churned
    churn_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    churn_risk_level: Mapped[str] = mapped_column(
        String(50), default="low", nullable=False
    )  # low, medium, high

    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="contributor_features")
    contributor: Mapped["User"] = relationship("User", back_populates="contributor_features")
    analysis_run: Mapped[Optional["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="contributor_features"
    )
    first_pr: Mapped[Optional["PullRequest"]] = relationship(
        "PullRequest", foreign_keys=[first_pr_id]
    )
