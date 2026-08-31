"""Repository domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.analysis_run import AnalysisRun
    from backend.app.models.comment import Comment
    from backend.app.models.commit import Commit
    from backend.app.models.contributor_feature import ContributorFeature
    from backend.app.models.ingestion_error import IngestionError
    from backend.app.models.issue import Issue
    from backend.app.models.pull_request import PullRequest


class Repository(Base, TimestampMixin):
    """SQLAlchemy model representing a tracked GitHub repository."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stars_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_issues_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fork: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pushed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    analysis_runs: Mapped[List["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
    issues: Mapped[List["Issue"]] = relationship(
        "Issue", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[List["Commit"]] = relationship(
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="repository", cascade="all, delete-orphan"
    )
    contributor_features: Mapped[List["ContributorFeature"]] = relationship(
        "ContributorFeature", back_populates="repository", cascade="all, delete-orphan"
    )
    ingestion_errors: Mapped[List["IngestionError"]] = relationship(
        "IngestionError", back_populates="repository", cascade="all, delete-orphan"
    )
