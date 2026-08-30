"""Analytics and contributor journey endpoints for ContributorPulse."""

import math
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.analytics.engine import RepositoryKPIEngine
from backend.app.db.session import get_db
from backend.app.models.base import utcnow
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.user import User
from backend.app.schemas.analytics import (
    ContributorCorrelationPoint,
    ContributorFeatureItem,
    CorrelationDataResponse,
    DistributionBucket,
    FunnelStage,
    HighRiskContributorItem,
    HighRiskListResponse,
    KPISummaryItem,
    KPISummaryResponse,
    MergeStatsResponse,
    PaginatedContributorsResponse,
    RepositoryComparisonItem,
    RepositoryComparisonResponse,
    RepositorySummaryResponse,
    ResponseDistributionResponse,
    RetentionFunnelResponse,
    ReviewTimelinePoint,
    ReviewTimelineResponse,
)
from backend.app.schemas.common import DataResponse, PaginationMeta

router = APIRouter(tags=["Analytics & Intelligence"])


def _get_repository_or_404(db: Session, owner: str, name: str) -> Repository:
    """Helper to fetch a repository or raise a structured 404."""
    repo = db.scalars(
        select(Repository).where(
            (func.lower(Repository.owner) == owner.lower())
            & (func.lower(Repository.name) == name.lower())
        )
    ).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{owner}/{name}' not found.",
        )
    return repo


@router.get(
    "/repositories/{owner}/{repo}/summary",
    response_model=DataResponse[RepositorySummaryResponse],
    summary="Repository Overview & Health Score",
    description="Retrieve repository activity summary, retention rates, and composite health score (0-100).",
)
def get_repository_summary(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[RepositorySummaryResponse]:
    """Return high-level summary and bounded health score."""
    repository = _get_repository_or_404(db, owner, repo)
    kpi_engine = RepositoryKPIEngine(db, repository.id)
    kpis = kpi_engine.calculate_kpis()

    total_commits = db.scalar(
        select(func.count()).select_from(PullRequest).where(PullRequest.repository_id == repository.id)
    ) or 0

    summary_data = RepositorySummaryResponse(
        repository_id=repository.id,
        owner=repository.owner,
        name=repository.name,
        full_name=repository.full_name,
        health_score=kpis["health_score"],
        total_contributors=kpis["total_contributors"],
        total_prs=kpis["sample_sizes"]["total_prs"],
        total_commits=total_commits,
        total_issues=0,
        retention_rate_30d=kpis["retention_rate_30d"],
        retention_rate_90d=kpis["retention_rate_90d"],
        merge_rate=kpis["merge_rate"],
        calculated_at=utcnow(),
    )
    return DataResponse(data=summary_data)


@router.get(
    "/repositories/{owner}/{repo}/kpis",
    response_model=DataResponse[KPISummaryResponse],
    summary="Comprehensive KPI Summary",
    description="Retrieve repository KPIs with values, measurement units, descriptions, and sample size metadata.",
)
def get_repository_kpis(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[KPISummaryResponse]:
    """Return all repository KPIs with detailed sample size provenance."""
    repository = _get_repository_or_404(db, owner, repo)
    kpi_engine = RepositoryKPIEngine(db, repository.id)
    kpis = kpi_engine.calculate_kpis()
    samples = kpis["sample_sizes"]

    kpi_items = {
        "retention_rate_30d": KPISummaryItem(
            name="30-Day Retention Rate",
            value=kpis["retention_rate_30d"],
            unit="%",
            sample_size=samples["eligible_30d_contributors"],
            description="Percentage of first-time contributors who made a repeat contribution within 30 days.",
        ),
        "retention_rate_90d": KPISummaryItem(
            name="90-Day Retention Rate",
            value=kpis["retention_rate_90d"],
            unit="%",
            sample_size=samples["eligible_90d_contributors"],
            description="Percentage of first-time contributors who made a repeat contribution within 90 days.",
        ),
        "merge_rate": KPISummaryItem(
            name="Pull Request Merge Rate",
            value=kpis["merge_rate"],
            unit="%",
            sample_size=samples["total_prs"],
            description="Percentage of total pull requests that were successfully merged.",
        ),
        "avg_response_time": KPISummaryItem(
            name="Average Response Time",
            value=kpis["avg_response_time_hours"],
            unit="hours",
            sample_size=samples["responded_prs_sample"],
            description="Average hours elapsed before a maintainer comments or reviews a first-time PR.",
        ),
        "avg_review_time": KPISummaryItem(
            name="Average Review Duration",
            value=kpis["avg_review_time_hours"],
            unit="hours",
            sample_size=samples["reviewed_prs_sample"],
            description="Average hours elapsed from PR creation to the first code review submission.",
        ),
        "contributor_growth": KPISummaryItem(
            name="Contributor Growth Rate",
            value=kpis["contributor_growth_rate"],
            unit="%",
            sample_size=samples["total_contributors"],
            description="Percentage change in new first-time contributors over the last 30 days.",
        ),
    }

    response_data = KPISummaryResponse(
        repository_id=repository.id,
        owner=repository.owner,
        name=repository.name,
        health_score=kpis["health_score"],
        kpis=kpi_items,
        calculated_at=utcnow(),
    )
    return DataResponse(data=response_data)


@router.get(
    "/repositories/{owner}/{repo}/contributors",
    response_model=DataResponse[PaginatedContributorsResponse],
    summary="Paginated Contributor Journeys",
    description="Retrieve paginated contributor features, onboarding velocities, retention status, and risk signals.",
)
def get_repository_contributors(
    owner: str,
    repo: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    experience_level: Optional[str] = Query(None, description="Filter by experience level (first_time, repeat, core)"),
    retention_status: Optional[str] = Query(None, description="Filter by retention status (onboarding, retained, churned)"),
    churn_risk_level: Optional[str] = Query(None, description="Filter by churn risk level (low, medium, high)"),
    is_active_maintainer: Optional[bool] = Query(None, description="Filter active maintainers"),
    search: Optional[str] = Query(None, description="Search by contributor login or name"),
    db: Session = Depends(get_db),
) -> DataResponse[PaginatedContributorsResponse]:
    """Return paginated and filtered contributor records."""
    repository = _get_repository_or_404(db, owner, repo)

    query = (
        select(ContributorFeature, User)
        .join(User, ContributorFeature.contributor_id == User.id)
        .where(ContributorFeature.repository_id == repository.id)
    )

    if experience_level:
        query = query.where(ContributorFeature.experience_level == experience_level.lower())
    if retention_status:
        query = query.where(ContributorFeature.retention_status == retention_status.lower())
    if churn_risk_level:
        query = query.where(ContributorFeature.churn_risk_level == churn_risk_level.lower())
    if is_active_maintainer is not None:
        query = query.where(ContributorFeature.is_active_maintainer == is_active_maintainer)
    if search:
        search_filter = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(User.login).like(search_filter) | func.lower(User.name).like(search_filter)
        )

    # Count total items
    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query) or 0

    # Paginate
    offset = (page - 1) * per_page
    results = db.execute(
        query.order_by(ContributorFeature.first_contribution_at.desc()).offset(offset).limit(per_page)
    ).all()

    items: List[ContributorFeatureItem] = []
    for feat, user in results:
        items.append(
            ContributorFeatureItem(
                contributor_id=user.id,
                login=user.login,
                name=user.name,
                avatar_url=user.avatar_url,
                first_contribution_at=feat.first_contribution_at,
                first_pr_merged=feat.first_pr_merged,
                first_response_time_hours=(
                    round(feat.first_response_time_seconds / 3600.0, 2)
                    if feat.first_response_time_seconds is not None
                    else None
                ),
                first_review_duration_hours=(
                    round(feat.first_pr_review_duration_seconds / 3600.0, 2)
                    if feat.first_pr_review_duration_seconds is not None
                    else None
                ),
                first_merge_duration_hours=(
                    round(feat.first_pr_merge_duration_seconds / 3600.0, 2)
                    if feat.first_pr_merge_duration_seconds is not None
                    else None
                ),
                total_prs=feat.total_prs,
                merged_prs=feat.merged_prs,
                total_commits=feat.total_commits,
                total_issues=feat.total_issues,
                total_reviews=feat.total_reviews,
                total_comments=feat.total_comments,
                experience_level=feat.experience_level,
                retention_status=feat.retention_status,
                is_retained_30d=feat.is_retained_30d,
                is_retained_60d=feat.is_retained_60d,
                is_retained_90d=feat.is_retained_90d,
                is_active_maintainer=feat.is_active_maintainer,
                has_weekend_contributions=feat.has_weekend_contributions,
                churn_risk_score=feat.churn_risk_score,
                churn_risk_level=feat.churn_risk_level,
                risk_reason=feat.risk_reason,
                last_active_at=feat.last_active_at,
            )
        )

    total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
    pagination = PaginationMeta(
        total_records=total_count,
        total_pages=total_pages,
        current_page=page,
        per_page=per_page,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return DataResponse(
        data=PaginatedContributorsResponse(
            items=items,
            pagination=pagination,
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/funnel",
    response_model=DataResponse[RetentionFunnelResponse],
    summary="Retention Funnel Data",
    description="Retrieve conversion counts and rates across onboarding and retention milestones.",
)
def get_retention_funnel(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[RetentionFunnelResponse]:
    """Return retention funnel stages and conversion metrics."""
    repository = _get_repository_or_404(db, owner, repo)

    features = db.scalars(
        select(ContributorFeature).where(ContributorFeature.repository_id == repository.id)
    ).all()

    total = len(features)
    pr_merged = sum(1 for f in features if f.first_pr_merged)
    retained_30d = sum(1 for f in features if f.is_retained_30d)
    retained_60d = sum(1 for f in features if f.is_retained_60d)
    retained_90d = sum(1 for f in features if f.is_retained_90d)

    def calc_rate(count: int) -> float:
        return round((count / total) * 100.0, 1) if total > 0 else 0.0

    stages = [
        FunnelStage(stage="Initial Contribution", count=total, conversion_rate=100.0 if total > 0 else 0.0),
        FunnelStage(stage="First PR Merged", count=pr_merged, conversion_rate=calc_rate(pr_merged)),
        FunnelStage(stage="Retained 30 Days", count=retained_30d, conversion_rate=calc_rate(retained_30d)),
        FunnelStage(stage="Retained 60 Days", count=retained_60d, conversion_rate=calc_rate(retained_60d)),
        FunnelStage(stage="Retained 90 Days", count=retained_90d, conversion_rate=calc_rate(retained_90d)),
    ]

    return DataResponse(
        data=RetentionFunnelResponse(
            repository_id=repository.id,
            total_first_time=total,
            stages=stages,
            calculated_at=utcnow(),
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/response-distribution",
    response_model=DataResponse[ResponseDistributionResponse],
    summary="Response Time Distribution",
    description="Retrieve binned response time distribution and central tendency measures.",
)
def get_response_distribution(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[ResponseDistributionResponse]:
    """Return response-time bracket distribution."""
    repository = _get_repository_or_404(db, owner, repo)

    features = db.scalars(
        select(ContributorFeature).where(ContributorFeature.repository_id == repository.id)
    ).all()

    b_under_12 = 0
    b_12_24 = 0
    b_24_48 = 0
    b_48_72 = 0
    b_over_72 = 0
    b_no_resp = 0

    response_hours_list: List[float] = []

    for f in features:
        if f.first_response_time_seconds is None:
            b_no_resp += 1
        else:
            h = f.first_response_time_seconds / 3600.0
            response_hours_list.append(h)
            if h < 12.0:
                b_under_12 += 1
            elif h <= 24.0:
                b_12_24 += 1
            elif h <= 48.0:
                b_24_48 += 1
            elif h <= 72.0:
                b_48_72 += 1
            else:
                b_over_72 += 1

    total = len(features)

    def pct(c: int) -> float:
        return round((c / total) * 100.0, 1) if total > 0 else 0.0

    buckets = [
        DistributionBucket(bucket_label="< 12h", count=b_under_12, percentage=pct(b_under_12)),
        DistributionBucket(bucket_label="12 - 24h", count=b_12_24, percentage=pct(b_12_24)),
        DistributionBucket(bucket_label="24 - 48h", count=b_24_48, percentage=pct(b_24_48)),
        DistributionBucket(bucket_label="48 - 72h", count=b_48_72, percentage=pct(b_48_72)),
        DistributionBucket(bucket_label="> 72h", count=b_over_72, percentage=pct(b_over_72)),
        DistributionBucket(bucket_label="No Response", count=b_no_resp, percentage=pct(b_no_resp)),
    ]

    avg_resp = round(sum(response_hours_list) / len(response_hours_list), 2) if response_hours_list else None
    med_resp = None
    if response_hours_list:
        sorted_h = sorted(response_hours_list)
        mid = len(sorted_h) // 2
        med_resp = round(sorted_h[mid], 2)

    return DataResponse(
        data=ResponseDistributionResponse(
            repository_id=repository.id,
            total_evaluated_prs=total,
            buckets=buckets,
            avg_response_hours=avg_resp,
            median_response_hours=med_resp,
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/review-timeline",
    response_model=DataResponse[ReviewTimelineResponse],
    summary="Review Speed Timeline",
    description="Retrieve chronological review and response velocity trends grouped by month.",
)
def get_review_timeline(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[ReviewTimelineResponse]:
    """Return historical timeline of review speeds."""
    repository = _get_repository_or_404(db, owner, repo)

    features = db.scalars(
        select(ContributorFeature)
        .where(
            (ContributorFeature.repository_id == repository.id)
            & (ContributorFeature.first_contribution_at.is_not(None))
        )
        .order_by(ContributorFeature.first_contribution_at.asc())
    ).all()

    # Group by YYYY-MM
    grouped: Dict[str, List[ContributorFeature]] = {}
    for f in features:
        if f.first_contribution_at:
            period = f.first_contribution_at.strftime("%Y-%m")
            grouped.setdefault(period, []).append(f)

    timeline_points: List[ReviewTimelinePoint] = []
    for period, items in sorted(grouped.items()):
        rev_times = [
            i.first_pr_review_duration_seconds / 3600.0
            for i in items
            if i.first_pr_review_duration_seconds is not None
        ]
        resp_times = [
            i.first_response_time_seconds / 3600.0
            for i in items
            if i.first_response_time_seconds is not None
        ]

        timeline_points.append(
            ReviewTimelinePoint(
                period=period,
                avg_review_hours=round(sum(rev_times) / len(rev_times), 2) if rev_times else None,
                avg_response_hours=round(sum(resp_times) / len(resp_times), 2) if resp_times else None,
                reviews_count=len(rev_times),
                prs_count=len(items),
            )
        )

    return DataResponse(
        data=ReviewTimelineResponse(
            repository_id=repository.id,
            timeline=timeline_points,
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/merge-stats",
    response_model=DataResponse[MergeStatsResponse],
    summary="Pull Request Merge Statistics",
    description="Retrieve merge success rates, outcomes, and duration distributions.",
)
def get_merge_stats(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[MergeStatsResponse]:
    """Return PR merge metrics and durations."""
    repository = _get_repository_or_404(db, owner, repo)

    prs = db.scalars(
        select(PullRequest).where(PullRequest.repository_id == repository.id)
    ).all()

    total_prs = len(prs)
    merged_prs = sum(1 for p in prs if p.is_merged)
    closed_unmerged = sum(1 for p in prs if p.state == "closed" and not p.is_merged)
    open_prs = sum(1 for p in prs if p.state == "open")
    merge_rate = round((merged_prs / total_prs) * 100.0, 1) if total_prs > 0 else 0.0

    merge_durations: List[float] = []
    for p in prs:
        if p.is_merged and p.merged_at and p.created_at:
            duration_hours = max(0.0, (p.merged_at - p.created_at).total_seconds() / 3600.0)
            merge_durations.append(duration_hours)

    avg_merge_dur = round(sum(merge_durations) / len(merge_durations), 2) if merge_durations else None
    med_merge_dur = None
    if merge_durations:
        sorted_d = sorted(merge_durations)
        mid = len(sorted_d) // 2
        med_merge_dur = round(sorted_d[mid], 2)

    return DataResponse(
        data=MergeStatsResponse(
            repository_id=repository.id,
            total_prs=total_prs,
            merged_prs=merged_prs,
            closed_unmerged_prs=closed_unmerged,
            open_prs=open_prs,
            merge_rate=merge_rate,
            avg_merge_duration_hours=avg_merge_dur,
            median_merge_duration_hours=med_merge_dur,
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/correlations",
    response_model=DataResponse[CorrelationDataResponse],
    summary="Correlation & Feature Analysis Data",
    description="Retrieve contributor-level feature vectors suitable for correlation and scatter analysis.",
)
def get_correlation_data(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[CorrelationDataResponse]:
    """Return tabular contributor metrics for scatter/correlation analysis."""
    repository = _get_repository_or_404(db, owner, repo)

    results = db.execute(
        select(ContributorFeature, User)
        .join(User, ContributorFeature.contributor_id == User.id)
        .where(ContributorFeature.repository_id == repository.id)
    ).all()

    points: List[ContributorCorrelationPoint] = []
    for feat, user in results:
        points.append(
            ContributorCorrelationPoint(
                contributor_id=user.id,
                login=user.login,
                first_response_time_hours=(
                    round(feat.first_response_time_seconds / 3600.0, 2)
                    if feat.first_response_time_seconds is not None
                    else None
                ),
                first_review_duration_hours=(
                    round(feat.first_pr_review_duration_seconds / 3600.0, 2)
                    if feat.first_pr_review_duration_seconds is not None
                    else None
                ),
                total_contributions=(
                    feat.total_prs + feat.total_commits + feat.total_issues + feat.total_reviews + feat.total_comments
                ),
                total_prs=feat.total_prs,
                is_retained_30d=feat.is_retained_30d,
                is_retained_90d=feat.is_retained_90d,
                churn_risk_score=feat.churn_risk_score,
            )
        )

    return DataResponse(
        data=CorrelationDataResponse(
            repository_id=repository.id,
            sample_size=len(points),
            features=points,
        )
    )


@router.get(
    "/repositories/{owner}/{repo}/high-risk-contributors",
    response_model=DataResponse[HighRiskListResponse],
    summary="High Churn Risk Contributors",
    description="Retrieve contributors identified with high churn risk, including risk scores and reasons.",
)
def get_high_risk_contributors(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> DataResponse[HighRiskListResponse]:
    """Return high churn risk contributors and explanatory penalty triggers."""
    repository = _get_repository_or_404(db, owner, repo)

    results = db.execute(
        select(ContributorFeature, User)
        .join(User, ContributorFeature.contributor_id == User.id)
        .where(
            (ContributorFeature.repository_id == repository.id)
            & (ContributorFeature.churn_risk_level == "high")
        )
        .order_by(ContributorFeature.churn_risk_score.desc())
    ).all()

    items: List[HighRiskContributorItem] = []
    for feat, user in results:
        items.append(
            HighRiskContributorItem(
                contributor_id=user.id,
                login=user.login,
                avatar_url=user.avatar_url,
                churn_risk_score=feat.churn_risk_score,
                churn_risk_level=feat.churn_risk_level,
                risk_reason=feat.risk_reason,
                first_contribution_at=feat.first_contribution_at,
                total_prs=feat.total_prs,
                first_pr_merged=feat.first_pr_merged,
            )
        )

    return DataResponse(
        data=HighRiskListResponse(
            repository_id=repository.id,
            high_risk_count=len(items),
            items=items,
        )
    )


@router.get(
    "/repositories/compare",
    response_model=DataResponse[RepositoryComparisonResponse],
    summary="Comparative Repository Analysis",
    description="Compare KPIs, retention metrics, and health scores across multiple repositories.",
)
def compare_repositories(
    repos: str = Query(..., description="Comma-separated repository full names, e.g. 'owner1/repo1,owner2/repo2'"),
    db: Session = Depends(get_db),
) -> DataResponse[RepositoryComparisonResponse]:
    """Compare multiple repositories side by side."""
    repo_names = [r.strip() for r in repos.split(",") if r.strip()]
    if not repo_names:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parameter 'repos' must contain at least one repository full name.",
        )

    comparison_items: List[RepositoryComparisonItem] = []

    for full_name in repo_names:
        if "/" not in full_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid repository format '{full_name}'. Must be 'owner/name'.",
            )
        owner, name = full_name.split("/", 1)
        repo = db.scalars(
            select(Repository).where(
                (func.lower(Repository.owner) == owner.lower())
                & (func.lower(Repository.name) == name.lower())
            )
        ).first()

        if repo:
            kpi_engine = RepositoryKPIEngine(db, repo.id)
            kpis = kpi_engine.calculate_kpis()
            comparison_items.append(
                RepositoryComparisonItem(
                    repository_id=repo.id,
                    full_name=repo.full_name,
                    health_score=kpis["health_score"],
                    total_contributors=kpis["total_contributors"],
                    total_prs=kpis["sample_sizes"]["total_prs"],
                    retention_rate_30d=kpis["retention_rate_30d"],
                    retention_rate_90d=kpis["retention_rate_90d"],
                    merge_rate=kpis["merge_rate"],
                    avg_response_hours=kpis["avg_response_time_hours"],
                    avg_review_hours=kpis["avg_review_time_hours"],
                )
            )

    return DataResponse(
        data=RepositoryComparisonResponse(
            repositories=comparison_items,
            compared_at=utcnow(),
        )
    )
