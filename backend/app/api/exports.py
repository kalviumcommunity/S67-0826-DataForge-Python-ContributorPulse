"""Exports and report generation endpoints for ContributorPulse."""

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.analytics.engine import RepositoryKPIEngine
from backend.app.db.session import get_db
from backend.app.models.base import utcnow
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.user import User

router = APIRouter(prefix="/repositories/{owner}/{repo}/exports", tags=["Exports & Reports"])


def _sanitize_filename_component(name: str) -> str:
    """Sanitize repository name or owner for secure attachment filenames."""
    sanitized = re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    return sanitized or "repository"


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
    "/contributors.csv",
    summary="Export Contributor Journeys (CSV)",
    description="Download a UTF-8 CSV export of all contributor retention features and risk metrics.",
)
def export_contributors_csv(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> Response:
    """Generate and stream contributor feature data as a CSV file."""
    repository = _get_repository_or_404(db, owner, repo)

    query = (
        select(ContributorFeature, User)
        .join(User, ContributorFeature.contributor_id == User.id)
        .where(ContributorFeature.repository_id == repository.id)
        .order_by(ContributorFeature.churn_risk_score.desc().nullslast(), User.login.asc())
    )
    records = db.execute(query).all()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = [
        "login",
        "name",
        "experience_level",
        "retention_status",
        "churn_risk_level",
        "churn_risk_score",
        "total_prs",
        "merged_prs",
        "total_commits",
        "total_reviews",
        "first_response_hours",
        "first_review_hours",
        "merge_hours",
        "has_weekend_contributions",
        "is_active_maintainer",
        "risk_reason",
    ]
    writer.writerow(headers)

    for feature, user in records:
        writer.writerow(
            [
                user.login,
                user.name or "",
                feature.experience_level or "first_time",
                feature.retention_status or "onboarding",
                feature.churn_risk_level or "low",
                feature.churn_risk_score if feature.churn_risk_score is not None else "",
                feature.total_prs or 0,
                feature.merged_prs or 0,
                feature.total_commits or 0,
                feature.total_reviews or 0,
                f"{feature.first_response_time_seconds / 3600.0:.2f}"
                if feature.first_response_time_seconds is not None
                else "",
                f"{feature.first_pr_review_duration_seconds / 3600.0:.2f}"
                if feature.first_pr_review_duration_seconds is not None
                else "",
                f"{feature.first_pr_merge_duration_seconds / 3600.0:.2f}"
                if feature.first_pr_merge_duration_seconds is not None
                else "",
                "true" if feature.has_weekend_contributions else "false",
                "true" if feature.is_active_maintainer else "false",
                feature.risk_reason or "",
            ]
        )

    safe_owner = _sanitize_filename_component(owner)
    safe_repo = _sanitize_filename_component(repo)
    filename = f"contributor_pulse_{safe_owner}_{safe_repo}_contributors.csv"

    return Response(
        content=output.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/kpis.csv",
    summary="Export Repository KPIs (CSV)",
    description="Download a UTF-8 CSV export of all computed repository KPIs, values, units, and sample sizes.",
)
def export_kpis_csv(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> Response:
    """Generate and stream computed repository KPIs as a CSV file."""
    repository = _get_repository_or_404(db, owner, repo)
    kpi_engine = RepositoryKPIEngine(db, repository.id)
    kpis = kpi_engine.calculate_kpis()
    sample_sizes = kpis.get("sample_sizes", {})

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    headers = ["metric_key", "metric_name", "value", "unit", "sample_size", "description"]
    writer.writerow(headers)

    definitions = [
        ("health_score", "Repository Health Score", kpis.get("health_score"), "/100", sample_sizes.get("total_contributors", 0), "Bounded composite repository health score."),
        ("retention_rate_30d", "30-Day Retention Rate", kpis.get("retention_rate_30d"), "%", sample_sizes.get("eligible_30d_contributors", 0), "Percentage of first-time contributors who returned within 30 days."),
        ("retention_rate_90d", "90-Day Retention Rate", kpis.get("retention_rate_90d"), "%", sample_sizes.get("eligible_90d_contributors", 0), "Percentage of first-time contributors who returned within 90 days."),
        ("merge_rate", "Pull Request Merge Rate", kpis.get("merge_rate"), "%", sample_sizes.get("total_prs", 0), "Percentage of total pull requests that were merged."),
        ("average_first_response_hours", "Average First Response Time", kpis.get("avg_response_time_hours"), "hours", sample_sizes.get("responded_prs_sample", 0), "Average maintainer latency until first comment or review."),
        ("average_review_hours", "Average Review Duration", kpis.get("avg_review_time_hours"), "hours", sample_sizes.get("reviewed_prs_sample", 0), "Average time elapsed until first code review."),
        ("contributor_growth_rate", "Contributor Growth Rate", kpis.get("contributor_growth_rate"), "%", sample_sizes.get("total_contributors", 0), "Growth rate of new contributors over the analyzed period."),
        ("high_risk_contributors_count", "High-Risk Contributor Count", kpis.get("high_risk_contributor_count"), "contributors", sample_sizes.get("total_contributors", 0), "Number of contributors flagged with churn risk score >= 0.60."),
    ]

    for key, name, val, unit, sample_size, desc in definitions:
        writer.writerow([key, name, val if val is not None else "", unit, sample_size, desc])

    safe_owner = _sanitize_filename_component(owner)
    safe_repo = _sanitize_filename_component(repo)
    filename = f"contributor_pulse_{safe_owner}_{safe_repo}_kpis.csv"

    return Response(
        content=output.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/report.json",
    summary="Download Full Report (JSON)",
    description="Download a structured, comprehensive JSON report containing all repository intelligence.",
)
def export_report_json(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> Response:
    """Generate and return comprehensive JSON intelligence report."""
    repository = _get_repository_or_404(db, owner, repo)
    kpi_engine = RepositoryKPIEngine(db, repository.id)
    kpis = kpi_engine.calculate_kpis()

    high_risk_query = (
        select(ContributorFeature, User)
        .join(User, ContributorFeature.contributor_id == User.id)
        .where(
            ContributorFeature.repository_id == repository.id,
            ContributorFeature.churn_risk_score >= 0.60,
        )
        .order_by(ContributorFeature.churn_risk_score.desc())
    )
    high_risk_records = db.execute(high_risk_query).all()
    high_risk_items = [
        {
            "login": u.login,
            "churn_risk_score": f.churn_risk_score,
            "churn_risk_level": f.churn_risk_level,
            "risk_reason": f.risk_reason,
            "experience_level": f.experience_level,
        }
        for f, u in high_risk_records
    ]

    report = {
        "report_title": f"ContributorPulse Intelligence Report - {repository.full_name}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": {
            "id": repository.id,
            "owner": repository.owner,
            "name": repository.name,
            "full_name": repository.full_name,
            "stars_count": repository.stars_count,
            "forks_count": repository.forks_count,
            "open_issues_count": repository.open_issues_count,
            "default_branch": repository.default_branch,
        },
        "health_score": kpis["health_score"],
        "kpis": kpis,
        "high_risk_contributors": {
            "total_flagged": len(high_risk_items),
            "items": high_risk_items,
        },
    }

    safe_owner = _sanitize_filename_component(owner)
    safe_repo = _sanitize_filename_component(repo)
    filename = f"contributor_pulse_{safe_owner}_{safe_repo}_report.json"

    json_str = json.dumps(report, indent=2, default=str)
    return Response(
        content=json_str.encode("utf-8"),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/report.html",
    summary="Download Printable Summary Report (HTML)",
    description="Download a styled, print-friendly HTML intelligence summary report.",
)
def export_report_html(
    owner: str,
    repo: str,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Generate and return styled print-friendly HTML report."""
    repository = _get_repository_or_404(db, owner, repo)
    kpi_engine = RepositoryKPIEngine(db, repository.id)
    kpis = kpi_engine.calculate_kpis()

    health_score = kpis.get("health_score", 0.0)
    health_color = "#28a745" if health_score >= 80 else ("#ffc107" if health_score >= 60 else "#dc3545")

    first_resp = kpis.get("avg_response_time_hours")
    first_resp_str = f"{first_resp:.1f} hrs" if first_resp is not None else "N/A"

    rev_time = kpis.get("avg_review_time_hours")
    rev_time_str = f"{rev_time:.1f} hrs" if rev_time is not None else "N/A"

    ret_30 = kpis.get("retention_rate_30d")
    ret_30_str = f"{ret_30:.1f}%" if ret_30 is not None else "N/A"

    ret_90 = kpis.get("retention_rate_90d")
    ret_90_str = f"{ret_90:.1f}%" if ret_90 is not None else "N/A"

    merge_rate = kpis.get("merge_rate")
    merge_rate_str = f"{merge_rate:.1f}%" if merge_rate is not None else "N/A"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ContributorPulse Report - {repository.full_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #24292e; max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        .header {{ border-bottom: 2px solid #e1e4e8; padding-bottom: 16px; margin-bottom: 24px; }}
        .badge {{ display: inline-block; padding: 4px 12px; font-weight: bold; border-radius: 12px; color: #fff; background-color: {health_color}; }}
        .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0; }}
        .card {{ background: #f6f8fa; border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; }}
        .card-title {{ font-size: 13px; color: #586069; font-weight: bold; text-transform: uppercase; }}
        .card-value {{ font-size: 24px; font-weight: bold; margin-top: 4px; color: #0366d6; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #e1e4e8; padding: 10px; text-align: left; }}
        th {{ background: #f6f8fa; }}
        .footer {{ margin-top: 40px; border-top: 1px solid #e1e4e8; padding-top: 12px; font-size: 12px; color: #586069; text-align: center; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 ContributorPulse Intelligence Report</h1>
        <h2>Repository: {repository.full_name}</h2>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Health Score: <span class="badge">{health_score:.1f} / 100</span></p>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-title">30-Day Retention</div>
            <div class="card-value">{ret_30_str}</div>
        </div>
        <div class="card">
            <div class="card-title">90-Day Retention</div>
            <div class="card-value">{ret_90_str}</div>
        </div>
        <div class="card">
            <div class="card-title">PR Merge Rate</div>
            <div class="card-value">{merge_rate_str}</div>
        </div>
        <div class="card">
            <div class="card-title">Avg First Response</div>
            <div class="card-value">{first_resp_str}</div>
        </div>
        <div class="card">
            <div class="card-title">Avg Review Time</div>
            <div class="card-value">{rev_time_str}</div>
        </div>
        <div class="card">
            <div class="card-title">High-Risk Contributors</div>
            <div class="card-value">{kpis.get('high_risk_contributor_count', 0)}</div>
        </div>
    </div>

    <h3>Executive Summary</h3>
    <p>This automated report measures first-time contributor onboarding velocity and retention for <strong>{repository.full_name}</strong>. Maintainers can utilize these benchmarks to reduce response latency, avoid contributor drop-off, and increase first-time retention.</p>

    <div class="footer">
        ContributorPulse &copy; {datetime.now(timezone.utc).year} - Open Source Maintainer Intelligence Platform
    </div>
</body>
</html>"""

    safe_owner = _sanitize_filename_component(owner)
    safe_repo = _sanitize_filename_component(repo)
    filename = f"contributor_pulse_{safe_owner}_{safe_repo}_report.html"

    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
