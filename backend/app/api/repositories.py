"""Repository details and summary endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.analyses import build_analysis_summary
from backend.app.db.session import get_db
from backend.app.models.analysis_run import AnalysisRun
from backend.app.models.commit import Commit
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.schemas.ingestion import RepositoryDetail, RepositoryResponse

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.get(
    "/{owner}/{repo}",
    response_model=RepositoryResponse,
    summary="Get Ingested Repository Details",
    description="Retrieve stored repository metadata, aggregated resource counts, and latest analysis status.",
)
def get_repository_by_name(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Retrieve persisted repository by owner and repo name."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        )

    repository = db.scalars(
        select(Repository).where(
            (func.lower(Repository.owner) == owner.lower())
            & (func.lower(Repository.name) == repo.lower())
        )
    ).first()

    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{owner}/{repo}' has not been ingested yet.",
        )

    # Aggregated counts
    total_prs = (
        db.scalar(
            select(func.count(PullRequest.id)).where(PullRequest.repository_id == repository.id)
        )
        or 0
    )

    total_issues = (
        db.scalar(select(func.count(Issue.id)).where(Issue.repository_id == repository.id)) or 0
    )

    total_commits = (
        db.scalar(select(func.count(Commit.id)).where(Commit.repository_id == repository.id)) or 0
    )

    distinct_contributors = (
        db.scalar(
            select(func.count(func.distinct(PullRequest.contributor_id))).where(
                PullRequest.repository_id == repository.id
            )
        )
        or 0
    )

    # Latest analysis run
    latest_run = db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.repository_id == repository.id)
        .order_by(AnalysisRun.initiated_at.desc())
    ).first()

    latest_summary = build_analysis_summary(latest_run, db) if latest_run else None

    detail = RepositoryDetail(
        id=repository.id,
        github_id=repository.github_id,
        owner=repository.owner,
        name=repository.name,
        full_name=repository.full_name,
        description=repository.description,
        primary_language=repository.primary_language,
        stars_count=repository.stars_count,
        forks_count=repository.forks_count,
        open_issues_count=repository.open_issues_count,
        default_branch=repository.default_branch,
        is_private=repository.is_private,
        is_fork=repository.is_fork,
        pushed_at=repository.pushed_at,
        created_at=repository.created_at,
        updated_at=repository.updated_at,
        total_contributors=distinct_contributors,
        total_prs=total_prs,
        total_issues=total_issues,
        total_commits=total_commits,
        latest_analysis_run=latest_summary,
    )

    return RepositoryResponse(
        status="success",
        data=detail,
        message=f"Repository '{repository.full_name}' retrieved successfully.",
    )
