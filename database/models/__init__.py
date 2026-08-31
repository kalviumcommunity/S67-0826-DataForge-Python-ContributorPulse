"""
Legacy compatibility package for database models.

Re-exports domain models from backend.app.models for backward compatibility.
New code should import directly from backend.app.models.
"""

from backend.app.models import (
    AnalysisRun,
    Base,
    Comment,
    Commit,
    ContributorFeature,
    IngestionError,
    Issue,
    PullRequest,
    Repository,
    Review,
    TimestampMixin,
    User,
    utcnow,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "utcnow",
    "Repository",
    "User",
    "PullRequest",
    "Issue",
    "Review",
    "Comment",
    "Commit",
    "ContributorFeature",
    "AnalysisRun",
    "IngestionError",
]
