"""Review domain model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntFK, BigIntPK

if TYPE_CHECKING:
    from backend.app.models.pull_request import PullRequest
    from backend.app.models.user import User


class Review(Base):
    """SQLAlchemy model representing a pull request review."""

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("pull_request_id", "github_id", name="uq_reviews_pr_github_id"),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    pull_request_id: Mapped[int] = mapped_column(
        BigIntFK, ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contributor_id: Mapped[Optional[int]] = mapped_column(
        BigIntFK, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    state: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="reviews")
    contributor: Mapped[Optional["User"]] = relationship("User", back_populates="reviews")
