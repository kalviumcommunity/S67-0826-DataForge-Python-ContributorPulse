"""Pydantic schemas for analysis runs and repository ingestion."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisCreateRequest(BaseModel):
    """Payload for triggering a repository analysis and ingestion."""

    owner: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        min_length=1,
        max_length=100,
        description="GitHub repository owner or organization login",
        json_schema_extra={"example": "kalviumcommunity"},
    )
    repo: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        min_length=1,
        max_length=100,
        description="GitHub repository name",
        json_schema_extra={"example": "S67-0826-DataForge-Python-ContributorPulse"},
    )
    max_pages: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Optional maximum number of pages to fetch per dataset",
        json_schema_extra={"example": 5},
    )


class AnalysisSummary(BaseModel):
    """Summary of an analysis execution and persisted entities."""

    run_id: str = Field(..., description="Unique UUID of the analysis run")
    repository_id: Optional[int] = Field(default=None, description="Database ID of repository")
    repository_name: Optional[str] = Field(default=None, description="Full repository name")
    status: str = Field(
        ...,
        description="Analysis status: pending, running, completed, partially_completed, failed",
        json_schema_extra={"example": "completed"},
    )
    initiated_at: datetime = Field(..., description="UTC timestamp when run started")
    completed_at: Optional[datetime] = Field(default=None, description="UTC timestamp when run finished")
    duration_seconds: Optional[float] = Field(default=None, description="Execution duration in seconds")
    total_prs_ingested: int = Field(default=0, description="Count of ingested pull requests")
    total_commits_ingested: int = Field(default=0, description="Count of ingested commits")
    total_issues_ingested: int = Field(default=0, description="Count of ingested issues")
    total_contributors_ingested: int = Field(default=0, description="Count of unique contributors")
    errors_count: int = Field(default=0, description="Number of non-fatal ingestion errors encountered")
    error_message: Optional[str] = Field(default=None, description="Error message if run failed")


class AnalysisResponse(BaseModel):
    """API envelope for analysis responses."""

    status: str = Field(default="success", description="Response status")
    data: AnalysisSummary = Field(..., description="Analysis execution metadata")
    message: Optional[str] = Field(default=None, description="Status message")


class RepositoryDetail(BaseModel):
    """Detailed repository entity with summary counts and latest analysis."""

    id: int = Field(..., description="Database primary key")
    github_id: int = Field(..., description="GitHub external ID")
    owner: str = Field(..., description="Repository owner")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository path owner/name")
    description: Optional[str] = Field(default=None, description="Repository description")
    primary_language: Optional[str] = Field(default=None, description="Primary programming language")
    stars_count: int = Field(default=0, description="Star count")
    forks_count: int = Field(default=0, description="Fork count")
    open_issues_count: int = Field(default=0, description="Open issues count")
    default_branch: str = Field(default="main", description="Default branch name")
    is_private: bool = Field(default=False, description="Whether repository is private")
    is_fork: bool = Field(default=False, description="Whether repository is a fork")
    pushed_at: Optional[datetime] = Field(default=None, description="Last push timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    total_contributors: int = Field(default=0, description="Total contributors stored")
    total_prs: int = Field(default=0, description="Total pull requests stored")
    total_issues: int = Field(default=0, description="Total issues stored")
    total_commits: int = Field(default=0, description="Total commits stored")
    latest_analysis_run: Optional[AnalysisSummary] = Field(
        default=None, description="Latest completed or executed analysis run"
    )


class RepositoryResponse(BaseModel):
    """API envelope for repository details."""

    status: str = Field(default="success", description="Response status")
    data: RepositoryDetail = Field(..., description="Repository details")
    message: Optional[str] = Field(default=None, description="Informational message")
