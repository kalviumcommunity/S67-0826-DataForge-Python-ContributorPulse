"""Pydantic schemas for analytics, KPIs, contributor journeys, and comparative reporting."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import PaginationMeta


class RepositorySummaryResponse(BaseModel):
    """Repository overview summary and composite health score."""

    model_config = ConfigDict(from_attributes=True)

    repository_id: int
    owner: str
    name: str
    full_name: str
    health_score: float = Field(..., ge=0.0, le=100.0, description="Bounded health score (0-100)")
    total_contributors: int = Field(..., ge=0)
    total_prs: int = Field(..., ge=0)
    total_commits: int = Field(..., ge=0)
    total_issues: int = Field(..., ge=0)
    retention_rate_30d: Optional[float] = Field(None, description="30-day first-time contributor retention percentage")
    retention_rate_90d: Optional[float] = Field(None, description="90-day first-time contributor retention percentage")
    merge_rate: float = Field(..., ge=0.0, le=100.0, description="Percentage of PRs merged")
    calculated_at: datetime


class KPISummaryItem(BaseModel):
    """Single KPI item with value, unit, status, and sample size."""

    name: str
    value: Optional[float] = None
    unit: str
    sample_size: int = 0
    description: str


class KPISummaryResponse(BaseModel):
    """Complete KPI summary payload with values, units, and sample sizes."""

    repository_id: int
    owner: str
    name: str
    health_score: float
    kpis: Dict[str, KPISummaryItem]
    calculated_at: datetime


class ContributorFeatureItem(BaseModel):
    """Contributor detail item with journey metrics and risk signals."""

    model_config = ConfigDict(from_attributes=True)

    contributor_id: int
    login: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    first_contribution_at: Optional[datetime] = None
    first_pr_merged: bool = False
    first_response_time_hours: Optional[float] = None
    first_review_duration_hours: Optional[float] = None
    first_merge_duration_hours: Optional[float] = None
    total_prs: int = 0
    merged_prs: int = 0
    total_commits: int = 0
    total_issues: int = 0
    total_reviews: int = 0
    total_comments: int = 0
    experience_level: str = "first_time"
    retention_status: str = "onboarding"
    is_retained_30d: bool = False
    is_retained_60d: bool = False
    is_retained_90d: bool = False
    is_active_maintainer: bool = False
    has_weekend_contributions: bool = False
    churn_risk_score: float = 0.0
    churn_risk_level: str = "low"
    risk_reason: Optional[str] = None
    last_active_at: Optional[datetime] = None


class PaginatedContributorsResponse(BaseModel):
    """Paginated contributor list with metadata."""

    items: List[ContributorFeatureItem]
    pagination: PaginationMeta


class FunnelStage(BaseModel):
    """Single step in the contributor onboarding/retention funnel."""

    stage: str
    count: int
    conversion_rate: float = Field(..., ge=0.0, le=100.0, description="Conversion percentage from base stage")


class RetentionFunnelResponse(BaseModel):
    """Multi-stage retention funnel data."""

    repository_id: int
    total_first_time: int
    stages: List[FunnelStage]
    calculated_at: datetime


class DistributionBucket(BaseModel):
    """Response time bucket with count and percentage."""

    bucket_label: str
    count: int
    percentage: float


class ResponseDistributionResponse(BaseModel):
    """Response-time distribution data across standard latency brackets."""

    repository_id: int
    total_evaluated_prs: int
    buckets: List[DistributionBucket]
    avg_response_hours: Optional[float] = None
    median_response_hours: Optional[float] = None


class ReviewTimelinePoint(BaseModel):
    """Review velocity data point grouped by interval."""

    period: str
    avg_review_hours: Optional[float] = None
    avg_response_hours: Optional[float] = None
    reviews_count: int = 0
    prs_count: int = 0


class ReviewTimelineResponse(BaseModel):
    """Time-series timeline of review and response speeds."""

    repository_id: int
    timeline: List[ReviewTimelinePoint]


class MergeStatsResponse(BaseModel):
    """Pull request merge outcome distribution and durations."""

    repository_id: int
    total_prs: int
    merged_prs: int
    closed_unmerged_prs: int
    open_prs: int
    merge_rate: float
    avg_merge_duration_hours: Optional[float] = None
    median_merge_duration_hours: Optional[float] = None


class ContributorCorrelationPoint(BaseModel):
    """Feature vector for correlation and scatter analysis."""

    contributor_id: int
    login: str
    first_response_time_hours: Optional[float] = None
    first_review_duration_hours: Optional[float] = None
    total_contributions: int = 0
    total_prs: int = 0
    is_retained_30d: bool = False
    is_retained_90d: bool = False
    churn_risk_score: float = 0.0


class CorrelationDataResponse(BaseModel):
    """Correlation-ready tabular feature data."""

    repository_id: int
    sample_size: int
    features: List[ContributorCorrelationPoint]


class HighRiskContributorItem(BaseModel):
    """Contributor identified as high churn risk with reasons."""

    contributor_id: int
    login: str
    avatar_url: Optional[str] = None
    churn_risk_score: float
    churn_risk_level: str
    risk_reason: Optional[str] = None
    first_contribution_at: Optional[datetime] = None
    total_prs: int = 0
    first_pr_merged: bool = False


class HighRiskListResponse(BaseModel):
    """List of high-risk contributors."""

    repository_id: int
    high_risk_count: int
    items: List[HighRiskContributorItem]


class RepositoryComparisonItem(BaseModel):
    """Comparative repository summary metrics."""

    repository_id: int
    full_name: str
    health_score: float
    total_contributors: int
    total_prs: int
    retention_rate_30d: Optional[float] = None
    retention_rate_90d: Optional[float] = None
    merge_rate: float
    avg_response_hours: Optional[float] = None
    avg_review_hours: Optional[float] = None


class RepositoryComparisonResponse(BaseModel):
    """Side-by-side comparison payload across multiple repositories."""

    repositories: List[RepositoryComparisonItem]
    compared_at: datetime
