"""Pull Request domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK

if TYPE_CHECKING:
    from backend.app.models.comment import Comment
    from backend.app.models.repository import Repository
    from backend.app.models.review import Review
    from backend.app.models.user import User


class PullRequest(Base):
    """SQLAlchemy model representing a pull request in a GitHub repository."""

    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_id", name="uq_pull_requests_repo_github_id"),
        UniqueConstraint("repository_id", "number", name="uq_pull_requests_repo_number"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    repository_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contributor_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # open, closed
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_merged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_first_time_contributor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    author_association: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    merged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    merge_commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    head_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    base_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    changed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    review_comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
    contributor: Mapped[Optional["User"]] = relationship("User", back_populates="pull_requests")
    reviews: Mapped[List["Review"]] = relationship(
        "Review", back_populates="pull_request", cascade="all, delete-orphan"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="pull_request", cascade="all, delete-orphan"
    )
