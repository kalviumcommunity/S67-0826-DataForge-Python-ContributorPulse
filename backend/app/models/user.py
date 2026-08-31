"""User / Contributor domain model."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from backend.app.models.comment import Comment
    from backend.app.models.commit import Commit
    from backend.app.models.contributor_feature import ContributorFeature
    from backend.app.models.issue import Issue
    from backend.app.models.pull_request import PullRequest
    from backend.app.models.review import Review


class User(Base, TimestampMixin):
    """SQLAlchemy model representing a GitHub user or repository contributor."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    html_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    user_type: Mapped[str] = mapped_column(String(50), default="User", nullable=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest", back_populates="contributor"
    )
    issues: Mapped[List["Issue"]] = relationship("Issue", back_populates="contributor")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="contributor")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="contributor")
    commits: Mapped[List["Commit"]] = relationship("Commit", back_populates="contributor")
    contributor_features: Mapped[List["ContributorFeature"]] = relationship(
        "ContributorFeature", back_populates="contributor"
    )
