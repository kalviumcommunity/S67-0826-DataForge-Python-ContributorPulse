"""Data cleaning, validation, and activity linking pipeline."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.base import utcnow
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.ingestion_error import IngestionError
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.review import Review
from backend.app.models.user import User
from backend.app.processing.cleaners import (
    clean_comment_data,
    clean_commit_data,
    clean_issue_data,
    clean_pull_request_data,
    clean_review_data,
    clean_user_data,
)

logger = logging.getLogger("contributor_pulse.processing_pipeline")


@dataclass
class ProcessingStatistics:
    """Consolidated summary of data cleaning, validation, and deduplication results."""

    input_count: int = 0
    output_count: int = 0
    duplicate_count: int = 0
    duplicates_detected_count: int = 0
    duplicates_removed_count: int = 0
    duplicates_retained_count: int = 0
    invalid_count: int = 0
    missing_values_handled_count: int = 0
    dataset_stats: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {
            "users": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
            "pull_requests": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
            "issues": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
            "reviews": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
            "comments": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
            "commits": {
                "input": 0,
                "output": 0,
                "duplicates": 0,
                "duplicates_detected": 0,
                "duplicates_removed": 0,
                "duplicates_retained": 0,
                "invalid": 0,
                "missing_handled": 0,
            },
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "input_count": self.input_count,
            "output_count": self.output_count,
            "duplicate_count": self.duplicate_count,
            "duplicates_detected_count": self.duplicates_detected_count,
            "duplicates_removed_count": self.duplicates_removed_count,
            "duplicates_retained_count": self.duplicates_retained_count,
            "invalid_count": self.invalid_count,
            "missing_values_handled_count": self.missing_values_handled_count,
            "dataset_stats": self.dataset_stats,
        }


class DataCleaningPipeline:
    """
    Reusable pipeline module that cleans, validates, links, and deduplicates ingested GitHub datasets.

    Deduplication Policy:
    - Ingested entities are scanned deterministically. The first canonical occurrence of an entity
      (by stable identifier: github_id, number, sha) is retained and updated with normalized fields.
    - Any pre-existing duplicate rows in the database (or repeated records within the run) are
      explicitly removed via session deletion (self.db.delete) to prevent analytical inflation.
    - Statistics track duplicates_detected, duplicates_removed, and duplicates_retained separately.
    """

    def __init__(
        self,
        db: Session,
        repository_id: int,
        analysis_run_id: Optional[int] = None,
    ) -> None:
        self.db = db
        self.repository_id = repository_id
        self.analysis_run_id = analysis_run_id
        self.stats = ProcessingStatistics()

    def log_quarantine(
        self,
        stage: str,
        entity_type: str,
        entity_identifier: Optional[str],
        error_message: str,
        error_details: Optional[str] = None,
    ) -> None:
        """Record an invalid quarantined record into ingestion_errors."""
        err = IngestionError(
            repository_id=self.repository_id,
            analysis_run_id=self.analysis_run_id,
            stage=stage,
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            error_message=error_message,
            error_details=error_details,
            occurred_at=utcnow(),
        )
        self.db.add(err)
        self.db.flush()

    # --------------------------------------------------------------------------
    # Dataset Cleaning & Linking Stages
    # --------------------------------------------------------------------------

    def process_users(self) -> None:
        """Clean, validate, and deduplicate User records."""
        users = self.db.scalars(select(User).order_by(User.id.asc())).all()
        self.stats.dataset_stats["users"]["input"] = len(users)

        seen_github_ids: set[int] = set()
        seen_logins: set[str] = set()

        for user in users:
            raw_dict = {
                "id": user.github_id,
                "login": user.login,
                "name": user.name,
                "email": user.email,
                "avatar_url": user.avatar_url,
                "html_url": user.html_url,
                "user_type": user.user_type,
                "is_bot": user.is_bot,
            }

            cleaned, errors, missing_handled = clean_user_data(raw_dict)
            self.stats.dataset_stats["users"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["users"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="user",
                    entity_identifier=str(user.github_id or user.login),
                    error_message="; ".join(errors),
                )
                continue

            # Deterministic Deduplication: check if already seen
            is_dup = (
                cleaned["github_id"] is not None and cleaned["github_id"] in seen_github_ids
            ) or (cleaned["login"] and cleaned["login"].lower() in seen_logins)
            if is_dup:
                self.stats.dataset_stats["users"]["duplicates"] += 1
                self.stats.dataset_stats["users"]["duplicates_detected"] += 1
                self.db.delete(user)
                self.stats.dataset_stats["users"]["duplicates_removed"] += 1
                continue

            if cleaned["github_id"] is not None:
                seen_github_ids.add(cleaned["github_id"])
            if cleaned["login"]:
                seen_logins.add(cleaned["login"].lower())

            # Apply normalized values
            user.login = cleaned["login"]
            user.name = cleaned["name"]
            user.email = cleaned["email"]
            user.avatar_url = cleaned["avatar_url"]
            user.html_url = cleaned["html_url"]
            user.user_type = cleaned["user_type"]
            user.is_bot = cleaned["is_bot"]
            user.updated_at = utcnow()
            self.stats.dataset_stats["users"]["output"] += 1

        self.stats.dataset_stats["users"]["duplicates_retained"] = len(seen_github_ids)
        self.db.flush()

    def process_pull_requests(self) -> None:
        """Clean, validate, deduplicate, and link PullRequest records for this repo."""
        prs = self.db.scalars(
            select(PullRequest)
            .where(PullRequest.repository_id == self.repository_id)
            .order_by(PullRequest.id.asc())
        ).all()
        self.stats.dataset_stats["pull_requests"]["input"] = len(prs)

        seen_numbers: set[int] = set()
        seen_github_ids: set[int] = set()

        for pr in prs:
            raw_dict = {
                "id": pr.github_id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "draft": pr.is_draft,
                "is_merged": pr.is_merged,
                "is_first_time_contributor": pr.is_first_time_contributor,
                "author_association": pr.author_association,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "closed_at": pr.closed_at,
                "merged_at": pr.merged_at,
                "merge_commit_sha": pr.merge_commit_sha,
                "head_sha": pr.head_sha,
                "base_branch": pr.base_branch,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files": pr.changed_files,
                "comments": pr.comments_count,
                "review_comments": pr.review_comments_count,
            }

            cleaned, errors, missing_handled = clean_pull_request_data(raw_dict)
            self.stats.dataset_stats["pull_requests"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["pull_requests"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="pull_request",
                    entity_identifier=str(pr.number),
                    error_message="; ".join(errors),
                )
                continue

            # Deterministic Deduplication: check if already seen
            is_dup = (
                cleaned["github_id"] is not None and cleaned["github_id"] in seen_github_ids
            ) or (cleaned["number"] in seen_numbers)
            if is_dup:
                self.stats.dataset_stats["pull_requests"]["duplicates"] += 1
                self.stats.dataset_stats["pull_requests"]["duplicates_detected"] += 1
                self.db.delete(pr)
                self.stats.dataset_stats["pull_requests"]["duplicates_removed"] += 1
                continue

            if cleaned["github_id"] is not None:
                seen_github_ids.add(cleaned["github_id"])
            seen_numbers.add(cleaned["number"])

            # Apply normalized values
            pr.title = cleaned["title"]
            pr.body = cleaned["body"]
            pr.state = cleaned["state"]
            pr.is_draft = cleaned["is_draft"]
            pr.is_merged = cleaned["is_merged"]
            pr.is_first_time_contributor = cleaned["is_first_time_contributor"]
            pr.author_association = cleaned["author_association"]
            pr.created_at = cleaned["created_at"]
            pr.updated_at = cleaned["updated_at"]
            pr.closed_at = cleaned["closed_at"]
            pr.merged_at = cleaned["merged_at"]
            pr.merge_commit_sha = cleaned["merge_commit_sha"]
            pr.head_sha = cleaned["head_sha"]
            pr.base_branch = cleaned["base_branch"]
            pr.additions = cleaned["additions"]
            pr.deletions = cleaned["deletions"]
            pr.changed_files = cleaned["changed_files"]
            pr.comments_count = cleaned["comments_count"]
            pr.review_comments_count = cleaned["review_comments_count"]
            self.stats.dataset_stats["pull_requests"]["output"] += 1

        self.stats.dataset_stats["pull_requests"]["duplicates_retained"] = len(seen_numbers)
        self.db.flush()

    def process_issues(self) -> None:
        """Clean, validate, deduplicate, and link Issue records for this repo."""
        issues = self.db.scalars(
            select(Issue).where(Issue.repository_id == self.repository_id).order_by(Issue.id.asc())
        ).all()
        self.stats.dataset_stats["issues"]["input"] = len(issues)

        seen_numbers: set[int] = set()
        seen_github_ids: set[int] = set()

        for issue in issues:
            raw_dict = {
                "id": issue.github_id,
                "number": issue.number,
                "title": issue.title,
                "body": issue.body,
                "state": issue.state,
                "is_pull_request": issue.is_pull_request,
                "comments": issue.comments_count,
                "created_at": issue.created_at,
                "updated_at": issue.updated_at,
                "closed_at": issue.closed_at,
            }

            cleaned, errors, missing_handled = clean_issue_data(raw_dict)
            self.stats.dataset_stats["issues"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["issues"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="issue",
                    entity_identifier=str(issue.number),
                    error_message="; ".join(errors),
                )
                continue

            is_dup = (
                cleaned["github_id"] is not None and cleaned["github_id"] in seen_github_ids
            ) or (cleaned["number"] in seen_numbers)
            if is_dup:
                self.stats.dataset_stats["issues"]["duplicates"] += 1
                self.stats.dataset_stats["issues"]["duplicates_detected"] += 1
                self.db.delete(issue)
                self.stats.dataset_stats["issues"]["duplicates_removed"] += 1
                continue

            if cleaned["github_id"] is not None:
                seen_github_ids.add(cleaned["github_id"])
            seen_numbers.add(cleaned["number"])

            # Apply normalized values
            issue.title = cleaned["title"]
            issue.body = cleaned["body"]
            issue.state = cleaned["state"]
            issue.is_pull_request = cleaned["is_pull_request"]
            issue.comments_count = cleaned["comments_count"]
            issue.created_at = cleaned["created_at"]
            issue.updated_at = cleaned["updated_at"]
            issue.closed_at = cleaned["closed_at"]
            self.stats.dataset_stats["issues"]["output"] += 1

        self.stats.dataset_stats["issues"]["duplicates_retained"] = len(seen_numbers)
        self.db.flush()

    def process_reviews(self) -> None:
        """Clean, validate, deduplicate, and link Review records for PRs belonging to this repo."""
        prs = self.db.scalars(
            select(PullRequest).where(PullRequest.repository_id == self.repository_id)
        ).all()
        pr_ids = {pr.id for pr in prs}

        if not pr_ids:
            return

        reviews = self.db.scalars(
            select(Review).where(Review.pull_request_id.in_(pr_ids)).order_by(Review.id.asc())
        ).all()
        self.stats.dataset_stats["reviews"]["input"] = len(reviews)

        seen_github_ids: set[int] = set()

        for review in reviews:
            raw_dict = {
                "id": review.github_id,
                "state": review.state,
                "body": review.body,
                "submitted_at": review.submitted_at,
            }

            cleaned, errors, missing_handled = clean_review_data(raw_dict)
            self.stats.dataset_stats["reviews"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["reviews"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="review",
                    entity_identifier=str(review.github_id),
                    error_message="; ".join(errors),
                )
                continue

            if cleaned["github_id"] is not None and cleaned["github_id"] in seen_github_ids:
                self.stats.dataset_stats["reviews"]["duplicates"] += 1
                self.stats.dataset_stats["reviews"]["duplicates_detected"] += 1
                self.db.delete(review)
                self.stats.dataset_stats["reviews"]["duplicates_removed"] += 1
                continue

            if cleaned["github_id"] is not None:
                seen_github_ids.add(cleaned["github_id"])

            review.state = cleaned["state"]
            review.body = cleaned["body"]
            review.submitted_at = cleaned["submitted_at"]
            self.stats.dataset_stats["reviews"]["output"] += 1

        self.stats.dataset_stats["reviews"]["duplicates_retained"] = len(seen_github_ids)
        self.db.flush()

    def process_comments(self) -> None:
        """Clean, validate, deduplicate, and link Comment records for this repo."""
        comments = self.db.scalars(
            select(Comment)
            .where(Comment.repository_id == self.repository_id)
            .order_by(Comment.id.asc())
        ).all()
        self.stats.dataset_stats["comments"]["input"] = len(comments)

        seen_github_ids: set[int] = set()

        for comment in comments:
            raw_dict = {
                "id": comment.github_id,
                "body": comment.body,
                "comment_type": comment.comment_type,
                "created_at": comment.created_at,
                "updated_at": comment.updated_at,
            }

            cleaned, errors, missing_handled = clean_comment_data(raw_dict)
            self.stats.dataset_stats["comments"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["comments"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="comment",
                    entity_identifier=str(comment.github_id),
                    error_message="; ".join(errors),
                )
                continue

            if cleaned["github_id"] is not None and cleaned["github_id"] in seen_github_ids:
                self.stats.dataset_stats["comments"]["duplicates"] += 1
                self.stats.dataset_stats["comments"]["duplicates_detected"] += 1
                self.db.delete(comment)
                self.stats.dataset_stats["comments"]["duplicates_removed"] += 1
                continue

            if cleaned["github_id"] is not None:
                seen_github_ids.add(cleaned["github_id"])

            comment.body = cleaned["body"]
            comment.comment_type = cleaned["comment_type"]
            comment.created_at = cleaned["created_at"]
            comment.updated_at = cleaned["updated_at"]
            self.stats.dataset_stats["comments"]["output"] += 1

        self.stats.dataset_stats["comments"]["duplicates_retained"] = len(seen_github_ids)
        self.db.flush()

    def process_commits(self) -> None:
        """Clean, validate, deduplicate, and link Commit records for this repo."""
        commits = self.db.scalars(
            select(Commit)
            .where(Commit.repository_id == self.repository_id)
            .order_by(Commit.id.asc())
        ).all()
        self.stats.dataset_stats["commits"]["input"] = len(commits)

        seen_shas: set[str] = set()

        for commit in commits:
            raw_dict = {
                "sha": commit.sha,
                "message": commit.message,
                "authored_at": commit.authored_at,
                "committed_at": commit.committed_at,
                "additions": commit.additions,
                "deletions": commit.deletions,
                "total_changes": commit.total_changes,
            }

            cleaned, errors, missing_handled = clean_commit_data(raw_dict)
            self.stats.dataset_stats["commits"]["missing_handled"] += missing_handled

            if errors or not cleaned:
                self.stats.dataset_stats["commits"]["invalid"] += 1
                self.log_quarantine(
                    stage="cleaning_validation",
                    entity_type="commit",
                    entity_identifier=commit.sha,
                    error_message="; ".join(errors),
                )
                continue

            if cleaned["sha"].lower() in seen_shas:
                self.stats.dataset_stats["commits"]["duplicates"] += 1
                self.stats.dataset_stats["commits"]["duplicates_detected"] += 1
                self.db.delete(commit)
                self.stats.dataset_stats["commits"]["duplicates_removed"] += 1
                continue

            seen_shas.add(cleaned["sha"].lower())

            commit.message = cleaned["message"]
            commit.authored_at = cleaned["authored_at"]
            commit.committed_at = cleaned["committed_at"]
            commit.additions = cleaned["additions"]
            commit.deletions = cleaned["deletions"]
            commit.total_changes = cleaned["total_changes"]
            self.stats.dataset_stats["commits"]["output"] += 1

        self.stats.dataset_stats["commits"]["duplicates_retained"] = len(seen_shas)
        self.db.flush()

    # --------------------------------------------------------------------------
    # Pipeline Execution Entrypoint
    # --------------------------------------------------------------------------

    def run(self) -> ProcessingStatistics:
        """Execute full cleaning, deduplication, and validation across all repository datasets."""
        logger.info("Executing DataCleaningPipeline for repository_id=%d...", self.repository_id)

        self.process_users()
        self.process_pull_requests()
        self.process_issues()
        self.process_reviews()
        self.process_comments()
        self.process_commits()

        # Compute aggregate totals
        self.stats.input_count = sum(s["input"] for s in self.stats.dataset_stats.values())
        self.stats.output_count = sum(s["output"] for s in self.stats.dataset_stats.values())
        self.stats.duplicate_count = sum(s["duplicates"] for s in self.stats.dataset_stats.values())
        self.stats.duplicates_detected_count = sum(
            s.get("duplicates_detected", 0) for s in self.stats.dataset_stats.values()
        )
        self.stats.duplicates_removed_count = sum(
            s.get("duplicates_removed", 0) for s in self.stats.dataset_stats.values()
        )
        self.stats.duplicates_retained_count = sum(
            s.get("duplicates_retained", 0) for s in self.stats.dataset_stats.values()
        )
        self.stats.invalid_count = sum(s["invalid"] for s in self.stats.dataset_stats.values())
        self.stats.missing_values_handled_count = sum(
            s["missing_handled"] for s in self.stats.dataset_stats.values()
        )

        self.db.commit()
        logger.info(
            "DataCleaningPipeline finished: %d in, %d out, %d dups detected, %d dups removed, %d invalid",
            self.stats.input_count,
            self.stats.output_count,
            self.stats.duplicates_detected_count,
            self.stats.duplicates_removed_count,
            self.stats.invalid_count,
        )
        return self.stats
