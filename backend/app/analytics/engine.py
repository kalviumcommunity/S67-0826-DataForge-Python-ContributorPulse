"""Retention feature engineering and repository KPI calculation engine."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.base import utcnow
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.contributor_feature import ContributorFeature
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.processing.normalizers import normalize_timestamp

logger = logging.getLogger("contributor_pulse.analytics_engine")


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Helper to ensure datetime is UTC-aware for safe subtraction."""
    return normalize_timestamp(dt)


class ContributorFeatureEngine:
    """Calculates onboarding journeys, retention flags, and transparent churn risk signals."""

    def __init__(
        self, db: Session, repository_id: int, analysis_run_id: Optional[int] = None
    ) -> None:
        self.db = db
        self.repository_id = repository_id
        self.analysis_run_id = analysis_run_id

    def calculate_for_contributor(self, contributor: User) -> ContributorFeature:
        """Calculate features for a single contributor and idempotently persist to contributor_features."""
        # 1. Fetch contributor's pull requests for this repo
        prs = self.db.scalars(
            select(PullRequest)
            .where(
                (PullRequest.repository_id == self.repository_id)
                & (PullRequest.contributor_id == contributor.id)
            )
            .order_by(PullRequest.created_at.asc())
        ).all()

        # 2. Fetch issues, commits, reviews, comments
        issues = self.db.scalars(
            select(Issue)
            .where(
                (Issue.repository_id == self.repository_id)
                & (Issue.contributor_id == contributor.id)
            )
            .order_by(Issue.created_at.asc())
        ).all()

        commits = self.db.scalars(
            select(Commit)
            .where(
                (Commit.repository_id == self.repository_id)
                & (Commit.contributor_id == contributor.id)
            )
            .order_by(Commit.authored_at.asc())
        ).all()

        reviews_authored = self.db.scalars(
            select(Review)
            .join(PullRequest, Review.pull_request_id == PullRequest.id)
            .where(
                (PullRequest.repository_id == self.repository_id)
                & (Review.contributor_id == contributor.id)
            )
            .order_by(Review.submitted_at.asc())
        ).all()

        comments_authored = self.db.scalars(
            select(Comment)
            .where(
                (Comment.repository_id == self.repository_id)
                & (Comment.contributor_id == contributor.id)
            )
            .order_by(Comment.created_at.asc())
        ).all()

        # 3. Collect contribution timestamps for retention window calculations
        contribution_timestamps: List[datetime] = []
        for p in prs:
            utc_ts = _as_utc(p.created_at)
            if utc_ts:
                contribution_timestamps.append(utc_ts)
        for i in issues:
            utc_ts = _as_utc(i.created_at)
            if utc_ts:
                contribution_timestamps.append(utc_ts)
        for c in commits:
            utc_ts = _as_utc(c.authored_at)
            if utc_ts:
                contribution_timestamps.append(utc_ts)
        for r in reviews_authored:
            utc_ts = _as_utc(r.submitted_at)
            if utc_ts:
                contribution_timestamps.append(utc_ts)
        for cm in comments_authored:
            utc_ts = _as_utc(cm.created_at)
            if utc_ts:
                contribution_timestamps.append(utc_ts)

        contribution_timestamps.sort()

        first_contribution_at = contribution_timestamps[0] if contribution_timestamps else None
        last_active_at = contribution_timestamps[-1] if contribution_timestamps else None

        # 4. First PR onboarding velocity features
        first_pr = prs[0] if prs else None
        first_pr_id = first_pr.id if first_pr else None
        first_pr_merged = first_pr.is_merged if first_pr else False

        first_pr_review_duration_seconds: Optional[float] = None
        first_pr_merge_duration_seconds: Optional[float] = None
        first_response_time_seconds: Optional[float] = None

        first_pr_created_utc = _as_utc(first_pr.created_at) if first_pr else None

        if first_pr and first_pr_created_utc:
            # Merge duration
            first_pr_merged_utc = _as_utc(first_pr.merged_at)
            if first_pr.is_merged and first_pr_merged_utc:
                first_pr_merge_duration_seconds = max(
                    0.0, (first_pr_merged_utc - first_pr_created_utc).total_seconds()
                )

            # Reviews on first PR
            first_pr_reviews = self.db.scalars(
                select(Review)
                .where(Review.pull_request_id == first_pr.id)
                .order_by(Review.submitted_at.asc())
            ).all()

            if first_pr_reviews and first_pr_reviews[0].submitted_at:
                first_review_utc = _as_utc(first_pr_reviews[0].submitted_at)
                if first_review_utc:
                    first_pr_review_duration_seconds = max(
                        0.0, (first_review_utc - first_pr_created_utc).total_seconds()
                    )

            # First maintainer response (first comment or review not by the PR author)
            first_pr_comments = self.db.scalars(
                select(Comment)
                .where(
                    (Comment.pull_request_id == first_pr.id)
                    & (Comment.contributor_id != contributor.id)
                )
                .order_by(Comment.created_at.asc())
            ).all()

            response_candidates: List[datetime] = []
            if (
                first_pr_reviews
                and first_pr_reviews[0].contributor_id != contributor.id
                and first_pr_reviews[0].submitted_at
            ):
                r_utc = _as_utc(first_pr_reviews[0].submitted_at)
                if r_utc:
                    response_candidates.append(r_utc)
            if first_pr_comments and first_pr_comments[0].created_at:
                c_utc = _as_utc(first_pr_comments[0].created_at)
                if c_utc:
                    response_candidates.append(c_utc)

            if response_candidates:
                earliest_response = min(response_candidates)
                first_response_time_seconds = max(
                    0.0, (earliest_response - first_pr_created_utc).total_seconds()
                )

        # 5. Activity counts
        total_prs = len(prs)
        merged_prs = sum(1 for p in prs if p.is_merged)
        total_commits = len(commits)
        total_issues = len(issues)
        total_reviews = len(reviews_authored)
        total_comments = len(comments_authored)
        total_contributions = len(contribution_timestamps)

        # 6. Retention Return Windows (30d, 60d, 90d)
        is_retained_30d = False
        is_retained_60d = False
        is_retained_90d = False

        if first_contribution_at and len(contribution_timestamps) > 1:
            for ts in contribution_timestamps[1:]:
                delta_days = (ts - first_contribution_at).total_seconds() / 86400.0
                if 1.0 <= delta_days <= 30.0:
                    is_retained_30d = True
                if 30.0 < delta_days <= 60.0:
                    is_retained_60d = True
                if 30.0 < delta_days <= 90.0:
                    is_retained_90d = True

        # Determine retention status
        now_dt = utcnow()
        retention_status = "onboarding"
        if is_retained_30d or is_retained_60d or is_retained_90d:
            retention_status = "retained"
        elif first_contribution_at and (now_dt - first_contribution_at).days > 60:
            retention_status = "churned"

        # 7. Experience Level
        is_first_time = total_prs <= 1 and total_commits <= 1
        if total_contributions >= 10:
            experience_level = "core"
        elif total_contributions >= 2:
            experience_level = "repeat"
        else:
            experience_level = "first_time"

        # 8. Active Maintainer Flag
        is_active_maintainer = bool(
            total_reviews > 0
            or any(p.author_association in ("MEMBER", "OWNER", "COLLABORATOR") for p in prs)
            or contributor.user_type.lower() in ("member", "owner", "admin")
        )

        # 9. Weekend Contributions Flag
        has_weekend = any(ts.weekday() >= 5 for ts in contribution_timestamps)

        # 10. Rule-based, Transparent Churn Risk Scoring
        risk_score = 0.0
        risk_reasons: List[str] = []

        if first_pr:
            # Penalty for slow first response (> 48 hours)
            if first_response_time_seconds and first_response_time_seconds > 172800:
                risk_score += 0.30
                risk_reasons.append("Slow initial maintainer response (>48h)")
            elif (
                first_response_time_seconds is None
                and first_pr_created_utc
                and (now_dt - first_pr_created_utc).days > 3
            ):
                risk_score += 0.35
                risk_reasons.append("No response received on initial pull request")

            # Penalty if first PR was closed unmerged
            if first_pr.state == "closed" and not first_pr.is_merged:
                risk_score += 0.25
                risk_reasons.append("Initial pull request closed unmerged")

            # Penalty if no code reviews received
            if (
                first_pr_review_duration_seconds is None
                and first_pr_created_utc
                and (now_dt - first_pr_created_utc).days > 7
            ):
                risk_score += 0.20
                risk_reasons.append("No code review feedback on initial PR")

        # Penalty if contributor has only 1 contribution and inactive for > 60 days
        if (
            total_contributions == 1
            and first_contribution_at
            and (now_dt - first_contribution_at).days > 60
        ):
            risk_score += 0.25
            risk_reasons.append("No follow-up activity for >60 days")

        # Reward for repeat contribution / maintainer
        if total_contributions >= 3:
            risk_score = max(0.0, risk_score - 0.20)
        if is_active_maintainer:
            risk_score = max(0.0, risk_score - 0.30)

        churn_risk_score = round(max(0.0, min(1.0, risk_score)), 2)

        if churn_risk_score >= 0.60:
            churn_risk_level = "high"
        elif churn_risk_score >= 0.30:
            churn_risk_level = "medium"
        else:
            churn_risk_level = "low"

        risk_reason = "; ".join(risk_reasons) if risk_reasons else None

        # 11. Idempotent Upsert into contributor_features table
        cf = self.db.scalars(
            select(ContributorFeature).where(
                (ContributorFeature.repository_id == self.repository_id)
                & (ContributorFeature.contributor_id == contributor.id)
            )
        ).first()

        if cf:
            cf.analysis_run_id = self.analysis_run_id or cf.analysis_run_id
            cf.first_contribution_at = first_contribution_at
            cf.first_pr_id = first_pr_id
            cf.first_pr_merged = first_pr_merged
            cf.first_pr_review_duration_seconds = first_pr_review_duration_seconds
            cf.first_pr_merge_duration_seconds = first_pr_merge_duration_seconds
            cf.first_response_time_seconds = first_response_time_seconds
            cf.total_prs = total_prs
            cf.merged_prs = merged_prs
            cf.total_commits = total_commits
            cf.total_issues = total_issues
            cf.total_reviews = total_reviews
            cf.total_comments = total_comments
            cf.is_first_time_contributor = is_first_time
            cf.is_retained_30d = is_retained_30d
            cf.is_retained_60d = is_retained_60d
            cf.is_retained_90d = is_retained_90d
            cf.retention_status = retention_status
            cf.experience_level = experience_level
            cf.is_active_maintainer = is_active_maintainer
            cf.has_weekend_contributions = has_weekend
            cf.churn_risk_score = churn_risk_score
            cf.churn_risk_level = churn_risk_level
            cf.risk_reason = risk_reason
            cf.last_active_at = last_active_at
            cf.calculated_at = utcnow()
        else:
            cf = ContributorFeature(
                repository_id=self.repository_id,
                contributor_id=contributor.id,
                analysis_run_id=self.analysis_run_id,
                first_contribution_at=first_contribution_at,
                first_pr_id=first_pr_id,
                first_pr_merged=first_pr_merged,
                first_pr_review_duration_seconds=first_pr_review_duration_seconds,
                first_pr_merge_duration_seconds=first_pr_merge_duration_seconds,
                first_response_time_seconds=first_response_time_seconds,
                total_prs=total_prs,
                merged_prs=merged_prs,
                total_commits=total_commits,
                total_issues=total_issues,
                total_reviews=total_reviews,
                total_comments=total_comments,
                is_first_time_contributor=is_first_time,
                is_retained_30d=is_retained_30d,
                is_retained_60d=is_retained_60d,
                is_retained_90d=is_retained_90d,
                retention_status=retention_status,
                experience_level=experience_level,
                is_active_maintainer=is_active_maintainer,
                has_weekend_contributions=has_weekend,
                churn_risk_score=churn_risk_score,
                churn_risk_level=churn_risk_level,
                risk_reason=risk_reason,
                last_active_at=last_active_at,
                calculated_at=utcnow(),
            )
            self.db.add(cf)

        self.db.flush()
        return cf

    def calculate_all(self) -> List[ContributorFeature]:
        """Calculate and persist features for all contributors in this repository."""
        pr_users = select(PullRequest.contributor_id).where(
            (PullRequest.repository_id == self.repository_id)
            & (PullRequest.contributor_id.is_not(None))
        )
        commit_users = select(Commit.contributor_id).where(
            (Commit.repository_id == self.repository_id) & (Commit.contributor_id.is_not(None))
        )
        issue_users = select(Issue.contributor_id).where(
            (Issue.repository_id == self.repository_id) & (Issue.contributor_id.is_not(None))
        )

        all_user_ids = set(self.db.scalars(pr_users).all())
        all_user_ids.update(self.db.scalars(commit_users).all())
        all_user_ids.update(self.db.scalars(issue_users).all())

        if not all_user_ids:
            return []

        users = self.db.scalars(
            select(User).where(User.id.in_(list(all_user_ids)) & (User.is_bot.is_(False)))
        ).all()

        results: List[ContributorFeature] = []
        for user in users:
            feat = self.calculate_for_contributor(user)
            results.append(feat)

        self.db.commit()
        return results


def parse_period_days(period: Optional[str]) -> Optional[int]:
    """Parse period string into integer day count (e.g. '30d' -> 30, 'all' -> None)."""
    if not period:
        return None
    p = str(period).strip().lower()
    if p in ("30d", "last 30 days", "30"):
        return 30
    if p in ("90d", "last 90 days", "90"):
        return 90
    if p in ("180d", "last 180 days", "180"):
        return 180
    if p in ("365d", "last 365 days", "365", "1y", "1 year"):
        return 365
    return None


class RepositoryKPIEngine:
    """
    Calculates repository-level KPIs and transparent health scores.

    Period Filtering Semantics:
    - Contributor-level metrics (retention, contributor growth, churn risk, response/review speed samples)
      use contributor first_contribution_at / last_active_at timestamps to select the active cohort.
    - Event-level metrics (PR merge rates, counts) filter PullRequest records created within the trailing window.
    - When period is None or 'all', calculations evaluate full repository history.

    Retention Denominator & Observation Window Policy:
    - 30-Day Retention Denominator: Contributors whose first contribution was at least 30 days ago
      (so that a full 30-day return window has elapsed). If no contributors meet this threshold,
      the rate is returned as None (with sample_size=0) to distinguish insufficient data from 0% retention.
    - 90-Day Retention Denominator: Contributors whose first contribution was at least 90 days ago.
      If none meet the threshold, returns None with sample_size=0.
    """

    def __init__(self, db: Session, repository_id: int) -> None:
        self.db = db
        self.repository_id = repository_id

    def calculate_kpis(self, period: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute repository-level KPIs based on persisted clean data and contributor features,
        optionally scoped to a trailing time period (30d, 90d, 180d, 365d, all).

        Returns:
            Dict containing retention rates, merge rates, average review/response times,
            growth, high-risk counts, and composite health score.
        """
        now_dt = utcnow()
        days_limit = parse_period_days(period)
        cutoff_dt = (now_dt - timedelta(days=days_limit)) if days_limit else None

        # Fetch contributor features for this repository
        all_features = self.db.scalars(
            select(ContributorFeature).where(ContributorFeature.repository_id == self.repository_id)
        ).all()

        # Filter features by time period if specified
        if cutoff_dt:
            features = [
                f
                for f in all_features
                if (f.first_contribution_at and _as_utc(f.first_contribution_at) >= cutoff_dt)
                or (f.last_active_at and _as_utc(f.last_active_at) >= cutoff_dt)
            ]
        else:
            features = all_features

        total_contributors = len(features)

        # 1. Retention Rate (30d and 90d)
        # Denominator: only contributors whose first contribution occurred >= 30d (or >= 90d) ago
        eligible_30d = [
            f
            for f in features
            if f.first_contribution_at and (now_dt - _as_utc(f.first_contribution_at)).days >= 30
        ]
        retained_30d_count = sum(1 for f in eligible_30d if f.is_retained_30d)
        retention_rate_30d = (
            round((retained_30d_count / len(eligible_30d)) * 100.0, 1) if eligible_30d else None
        )

        eligible_90d = [
            f
            for f in features
            if f.first_contribution_at and (now_dt - _as_utc(f.first_contribution_at)).days >= 90
        ]
        retained_90d_count = sum(1 for f in eligible_90d if f.is_retained_90d)
        retention_rate_90d = (
            round((retained_90d_count / len(eligible_90d)) * 100.0, 1) if eligible_90d else None
        )

        # 2. Merge Rate (scoped to period if provided)
        pr_query = select(PullRequest).where(PullRequest.repository_id == self.repository_id)
        if cutoff_dt:
            pr_query = pr_query.where(PullRequest.created_at >= cutoff_dt)
        prs = self.db.scalars(pr_query).all()

        total_prs = len(prs)
        merged_prs = sum(1 for p in prs if p.is_merged)
        merge_rate = round((merged_prs / total_prs) * 100.0, 1) if total_prs > 0 else 0.0

        # 3. Average Review Time (hours) & Average Response Time (hours)
        review_times = [
            f.first_pr_review_duration_seconds / 3600.0
            for f in features
            if f.first_pr_review_duration_seconds is not None
        ]
        avg_review_time_hours = (
            round(sum(review_times) / len(review_times), 1) if review_times else None
        )

        response_times = [
            f.first_response_time_seconds / 3600.0
            for f in features
            if f.first_response_time_seconds is not None
        ]
        avg_response_time_hours = (
            round(sum(response_times) / len(response_times), 1) if response_times else None
        )

        # 4. High-Risk Contributor Count
        high_risk_count = sum(1 for f in features if f.churn_risk_level == "high")

        # 5. Contributor Growth (new contributors in last 30d vs previous 30d)
        new_last_30d = sum(
            1
            for f in features
            if f.first_contribution_at and (now_dt - _as_utc(f.first_contribution_at)).days <= 30
        )
        new_prev_30d = sum(
            1
            for f in features
            if f.first_contribution_at
            and 30 < (now_dt - _as_utc(f.first_contribution_at)).days <= 60
        )
        if new_prev_30d > 0:
            contributor_growth_rate = round(
                ((new_last_30d - new_prev_30d) / new_prev_30d) * 100.0, 1
            )
        elif new_last_30d > 0:
            contributor_growth_rate = 100.0
        else:
            contributor_growth_rate = 0.0

        # 6. Composite Repository Health Score (0 to 100)
        score = 0.0
        if total_contributors > 0 or total_prs > 0:
            # Component 1: Merge Rate (0 to 30)
            score += (merge_rate / 100.0) * 30.0

            # Component 2: Responsiveness (0 to 25)
            if avg_response_time_hours is not None:
                if avg_response_time_hours <= 24.0:
                    score += 25.0
                elif avg_response_time_hours <= 72.0:
                    score += 15.0
                else:
                    score += 5.0
            else:
                score += 15.0  # Neutral baseline when no response metric available

            # Component 3: Retention (0 to 25)
            if retention_rate_30d is not None:
                score += (retention_rate_30d / 100.0) * 25.0
            else:
                score += 12.5  # Neutral baseline for newly created / short-window cohorts

            # Component 4: Low Risk Contributors (0 to 20)
            if total_contributors > 0:
                high_risk_ratio = high_risk_count / total_contributors
                score += max(0.0, (1.0 - high_risk_ratio) * 20.0)
            else:
                score += 10.0

        health_score = round(max(0.0, min(100.0, score)), 1)

        return {
            "repository_id": self.repository_id,
            "period": period or "all",
            "total_contributors": total_contributors,
            "retention_rate_30d": retention_rate_30d,
            "retention_rate_90d": retention_rate_90d,
            "merge_rate": merge_rate,
            "avg_review_time_hours": avg_review_time_hours,
            "avg_response_time_hours": avg_response_time_hours,
            "contributor_growth_rate": contributor_growth_rate,
            "high_risk_contributor_count": high_risk_count,
            "health_score": health_score,
            "sample_sizes": {
                "total_contributors": total_contributors,
                "eligible_30d_contributors": len(eligible_30d),
                "eligible_90d_contributors": len(eligible_90d),
                "total_prs": total_prs,
                "reviewed_prs_sample": len(review_times),
                "responded_prs_sample": len(response_times),
            },
            "calculated_at": utcnow().isoformat(),
        }


class AnalyticsService:
    """Orchestrates retention feature engineering and repository KPI calculations."""

    def __init__(
        self, db: Session, repository_id: int, analysis_run_id: Optional[int] = None
    ) -> None:
        self.db = db
        self.repository_id = repository_id
        self.analysis_run_id = analysis_run_id
        self.feature_engine = ContributorFeatureEngine(db, repository_id, analysis_run_id)
        self.kpi_engine = RepositoryKPIEngine(db, repository_id)

    def run_pipeline(self) -> Dict[str, Any]:
        """Execute full feature engineering and KPI calculation."""
        features = self.feature_engine.calculate_all()
        kpis = self.kpi_engine.calculate_kpis()
        return {
            "features_calculated_count": len(features),
            "kpis": kpis,
        }
