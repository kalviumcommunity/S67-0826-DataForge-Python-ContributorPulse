"""Analysis execution and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.integrations.exceptions import (
    GitHubAuthenticationError,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubTimeoutError,
)
from backend.app.integrations.github import GitHubClient, get_github_client
from backend.app.models.analysis_run import AnalysisRun
from backend.app.models.ingestion_error import IngestionError
from backend.app.models.repository import Repository
from backend.app.schemas.ingestion import (
    AnalysisCreateRequest,
    AnalysisResponse,
    AnalysisSummary,
)
from backend.app.services.ingestion import IngestionService

router = APIRouter(prefix="/analyses", tags=["Analyses"])


def build_analysis_summary(run: AnalysisRun, db: Session) -> AnalysisSummary:
    """Helper to convert AnalysisRun ORM entity to AnalysisSummary schema."""
    repo = db.scalars(select(Repository).where(Repository.id == run.repository_id)).first()
    repo_name = repo.full_name if repo else None

    error_count = db.scalar(
        select(func.count(IngestionError.id)).where(IngestionError.analysis_run_id == run.id)
    ) or 0

    return AnalysisSummary(
        run_id=run.run_id,
        repository_id=run.repository_id,
        repository_name=repo_name,
        status=run.status.lower(),
        initiated_at=run.initiated_at,
        completed_at=run.completed_at,
        duration_seconds=run.duration_seconds,
        total_prs_ingested=run.total_prs_ingested,
        total_commits_ingested=run.total_commits_ingested,
        total_issues_ingested=run.total_issues_ingested,
        total_contributors_ingested=run.total_contributors_ingested,
        errors_count=error_count,
        error_message=run.error_message,
    )


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Repository Analysis",
    description="Ingests repository metadata, contributors, pull requests, issues, reviews, comments, and commits.",
)
def create_analysis(
    payload: AnalysisCreateRequest,
    db: Session = Depends(get_db),
    github_client: GitHubClient = Depends(get_github_client),
) -> AnalysisResponse:
    """Trigger a new repository analysis and ingestion run."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        )

    service = IngestionService(db=db, github_client=github_client)

    try:
        run = service.ingest_repository(
            owner=payload.owner,
            repo_name=payload.repo,
            max_pages=payload.max_pages,
        )
    except GitHubNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GitHub repository '{payload.owner}/{payload.repo}' was not found.",
        ) from exc
    except GitHubAuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub authentication token configured on server.",
        ) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"GitHub API rate limit exceeded: {exc.message}",
        ) from exc
    except GitHubForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to GitHub repository '{payload.owner}/{payload.repo}' is forbidden.",
        ) from exc
    except GitHubTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to GitHub API timed out.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest repository: {exc}",
        ) from exc

    summary = build_analysis_summary(run, db)
    return AnalysisResponse(
        status="success",
        data=summary,
        message=f"Repository analysis {summary.status}.",
    )


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get Analysis Run Status",
    description="Retrieve execution status, counts, and duration for a specific analysis run.",
)
def get_analysis_by_id(
    analysis_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    """Retrieve analysis run by UUID or integer ID."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        )

    stmt = select(AnalysisRun).where(AnalysisRun.run_id == analysis_id)
    if analysis_id.isdigit():
        stmt = select(AnalysisRun).where(
            (AnalysisRun.run_id == analysis_id) | (AnalysisRun.id == int(analysis_id))
        )

    run = db.scalars(stmt).first()
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run '{analysis_id}' not found.",
        )

    summary = build_analysis_summary(run, db)
    return AnalysisResponse(
        status="success",
        data=summary,
        message=f"Analysis run {summary.status}.",
    )
