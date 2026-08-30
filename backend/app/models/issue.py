"""Issue domain model."""

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
    from backend.app.models.user import User


class Issue(Base):
    """SQLAlchemy model representing an issue in a GitHub repository."""

    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("repository_id", "github_id", name="uq_issues_repo_github_id"),
        UniqueConstraint("repository_id", "number", name="uq_issues_repo_number"),
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
    is_pull_request: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="issues")
    contributor: Mapped[Optional["User"]] = relationship("User", back_populates="issues")
    comments: Mapped[List["Comment"]] = relationship(
        "Comment", back_populates="issue", cascade="all, delete-orphan"
    )
