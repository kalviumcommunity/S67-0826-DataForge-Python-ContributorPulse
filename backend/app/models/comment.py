"""Comment domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK

if TYPE_CHECKING:
    from backend.app.models.commit import Commit
    from backend.app.models.issue import Issue
    from backend.app.models.pull_request import PullRequest
    from backend.app.models.repository import Repository
    from backend.app.models.user import User


class Comment(Base):
    """SQLAlchemy model representing comments on PRs, issues, commits, or reviews."""

    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_id", name="uq_comments_repo_github_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    repository_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contributor_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pull_request_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=True, index=True
    )
    issue_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("issues.id", ondelete="CASCADE"), nullable=True, index=True
    )
    commit_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("commits.id", ondelete="CASCADE"), nullable=True, index=True
    )
    comment_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # issue, pull_request, review, commit
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="comments")
    contributor: Mapped[Optional["User"]] = relationship("User", back_populates="comments")
    pull_request: Mapped[Optional["PullRequest"]] = relationship(
        "PullRequest", back_populates="comments"
    )
    issue: Mapped[Optional["Issue"]] = relationship("Issue", back_populates="comments")
    commit: Mapped[Optional["Commit"]] = relationship("Commit", back_populates="comments")
