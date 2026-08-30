"""Repository ingestion service coordinating GitHub API extraction and idempotent PostgreSQL persistence."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.integrations.exceptions import GitHubAPIError, GitHubNotFoundError
from backend.app.integrations.github import GitHubClient
from backend.app.models.analysis_run import AnalysisRun
from backend.app.models.base import utcnow
from backend.app.models.comment import Comment
from backend.app.models.commit import Commit
from backend.app.models.ingestion_error import IngestionError
from backend.app.models.issue import Issue
from backend.app.models.pull_request import PullRequest
from backend.app.models.repository import Repository
from backend.app.models.review import Review
from backend.app.models.user import User

logger = logging.getLogger("contributor_pulse.ingestion_service")


def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 GitHub timestamp string to UTC-aware datetime."""
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


class IngestionService:
    """Service orchestrating GitHub dataset extraction and idempotent database persistence."""

    def __init__(self, db: Session, github_client: GitHubClient) -> None:
        self.db = db
        self.github_client = github_client

    # --------------------------------------------------------------------------
    # Idempotent Entity Upsert Helpers
    # --------------------------------------------------------------------------

    def upsert_user(self, raw_user: Optional[Dict[str, Any]]) -> Optional[User]:
        """Idempotently insert or update a GitHub User/Contributor record."""
        if not raw_user or not isinstance(raw_user, dict):
            return None

        github_id = raw_user.get("id")
        login = raw_user.get("login")
        if not github_id or not login:
            return None

        # Look up by github_id first, then login
        user = self.db.scalars(
            select(User).where((User.github_id == github_id) | (User.login == login))
        ).first()

        user_type = raw_user.get("type", "User")
        is_bot = user_type.lower() == "bot" or "[bot]" in login.lower()

        if user:
            user.login = login
            user.name = raw_user.get("name") or user.name
            user.email = raw_user.get("email") or user.email
            user.avatar_url = raw_user.get("avatar_url") or user.avatar_url
            user.html_url = raw_user.get("html_url") or user.html_url
            user.user_type = user_type
            user.is_bot = is_bot
            user.updated_at = utcnow()
        else:
            user = User(
                github_id=github_id,
                login=login,
                name=raw_user.get("name"),
                email=raw_user.get("email"),
                avatar_url=raw_user.get("avatar_url"),
                html_url=raw_user.get("html_url"),
                user_type=user_type,
                is_bot=is_bot,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.db.add(user)

        self.db.flush()
        return user

    def upsert_repository(self, raw_repo: Dict[str, Any]) -> Repository:
        """Idempotently insert or update a Repository record."""
        github_id = raw_repo["id"]
        full_name = raw_repo["full_name"]
        owner_name = raw_repo["owner"]["login"] if isinstance(raw_repo.get("owner"), dict) else raw_repo["owner"]
        repo_name = raw_repo["name"]

        repo = self.db.scalars(
            select(Repository).where((Repository.github_id == github_id) | (Repository.full_name == full_name))
        ).first()

        pushed_at_dt = parse_datetime(raw_repo.get("pushed_at"))

        if repo:
            repo.owner = owner_name
            repo.name = repo_name
            repo.full_name = full_name
            repo.description = raw_repo.get("description")
            repo.primary_language = raw_repo.get("language")
            repo.stars_count = raw_repo.get("stargazers_count", raw_repo.get("stars_count", 0))
            repo.forks_count = raw_repo.get("forks_count", 0)
            repo.open_issues_count = raw_repo.get("open_issues_count", 0)
            repo.default_branch = raw_repo.get("default_branch", "main")
            repo.is_private = bool(raw_repo.get("private", False))
            repo.is_fork = bool(raw_repo.get("fork", False))
            repo.pushed_at = pushed_at_dt
            repo.updated_at = utcnow()
        else:
            repo = Repository(
                github_id=github_id,
                owner=owner_name,
                name=repo_name,
                full_name=full_name,
                description=raw_repo.get("description"),
                primary_language=raw_repo.get("language"),
                stars_count=raw_repo.get("stargazers_count", raw_repo.get("stars_count", 0)),
                forks_count=raw_repo.get("forks_count", 0),
                open_issues_count=raw_repo.get("open_issues_count", 0),
                default_branch=raw_repo.get("default_branch", "main"),
                is_private=bool(raw_repo.get("private", False)),
                is_fork=bool(raw_repo.get("fork", False)),
                pushed_at=pushed_at_dt,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.db.add(repo)

        self.db.flush()
        return repo

    def upsert_pull_request(
        self,
        repository_id: int,
        raw_pr: Dict[str, Any],
        author_user_id: Optional[int],
    ) -> PullRequest:
        """Idempotently insert or update a PullRequest record."""
        github_id = raw_pr["id"]
        number = raw_pr["number"]

        pr = self.db.scalars(
            select(PullRequest).where(
                (PullRequest.repository_id == repository_id)
                & ((PullRequest.github_id == github_id) | (PullRequest.number == number))
            )
        ).first()

        created_at_dt = parse_datetime(raw_pr.get("created_at")) or utcnow()
        updated_at_dt = parse_datetime(raw_pr.get("updated_at"))
        closed_at_dt = parse_datetime(raw_pr.get("closed_at"))
        merged_at_dt = parse_datetime(raw_pr.get("merged_at"))
        is_merged = bool(merged_at_dt or raw_pr.get("merged", False))

        author_assoc = raw_pr.get("author_association", "")
        is_first_time = author_assoc == "FIRST_TIME_CONTRIBUTOR"

        if pr:
            pr.github_id = github_id
            pr.contributor_id = author_user_id
            pr.number = number
            pr.title = raw_pr.get("title", "")
            pr.body = raw_pr.get("body")
            pr.state = raw_pr.get("state", "open")
            pr.is_draft = bool(raw_pr.get("draft", False))
            pr.is_merged = is_merged
            pr.is_first_time_contributor = is_first_time
            pr.author_association = author_assoc
            pr.created_at = created_at_dt
            pr.updated_at = updated_at_dt
            pr.closed_at = closed_at_dt
            pr.merged_at = merged_at_dt
            pr.merge_commit_sha = raw_pr.get("merge_commit_sha")
            pr.head_sha = raw_pr.get("head", {}).get("sha") if isinstance(raw_pr.get("head"), dict) else None
            pr.base_branch = raw_pr.get("base", {}).get("ref") if isinstance(raw_pr.get("base"), dict) else None
            pr.additions = raw_pr.get("additions", pr.additions)
            pr.deletions = raw_pr.get("deletions", pr.deletions)
            pr.changed_files = raw_pr.get("changed_files", pr.changed_files)
            pr.comments_count = raw_pr.get("comments", pr.comments_count)
            pr.review_comments_count = raw_pr.get("review_comments", pr.review_comments_count)
        else:
            pr = PullRequest(
                github_id=github_id,
                repository_id=repository_id,
                contributor_id=author_user_id,
                number=number,
                title=raw_pr.get("title", ""),
                body=raw_pr.get("body"),
                state=raw_pr.get("state", "open"),
                is_draft=bool(raw_pr.get("draft", False)),
                is_merged=is_merged,
                is_first_time_contributor=is_first_time,
                author_association=author_assoc,
                created_at=created_at_dt,
                updated_at=updated_at_dt,
                closed_at=closed_at_dt,
                merged_at=merged_at_dt,
                merge_commit_sha=raw_pr.get("merge_commit_sha"),
                head_sha=raw_pr.get("head", {}).get("sha") if isinstance(raw_pr.get("head"), dict) else None,
                base_branch=raw_pr.get("base", {}).get("ref") if isinstance(raw_pr.get("base"), dict) else None,
                additions=raw_pr.get("additions", 0),
                deletions=raw_pr.get("deletions", 0),
                changed_files=raw_pr.get("changed_files", 0),
                comments_count=raw_pr.get("comments", 0),
                review_comments_count=raw_pr.get("review_comments", 0),
            )
            self.db.add(pr)

        self.db.flush()
        return pr

    def upsert_review(
        self,
        pull_request_id: int,
        raw_review: Dict[str, Any],
        reviewer_id: Optional[int],
    ) -> Review:
        """Idempotently insert or update a Review record."""
        github_id = raw_review["id"]

        review = self.db.scalars(
            select(Review).where(
                (Review.pull_request_id == pull_request_id) & (Review.github_id == github_id)
            )
        ).first()

        submitted_at_dt = parse_datetime(raw_review.get("submitted_at")) or utcnow()

        if review:
            review.contributor_id = reviewer_id
            review.state = raw_review.get("state", "COMMENTED")
            review.body = raw_review.get("body")
            review.submitted_at = submitted_at_dt
        else:
            review = Review(
                github_id=github_id,
                pull_request_id=pull_request_id,
                contributor_id=reviewer_id,
                state=raw_review.get("state", "COMMENTED"),
                body=raw_review.get("body"),
                submitted_at=submitted_at_dt,
            )
            self.db.add(review)

        self.db.flush()
        return review

    def upsert_issue(
        self,
        repository_id: int,
        raw_issue: Dict[str, Any],
        author_id: Optional[int],
    ) -> Issue:
        """Idempotently insert or update an Issue record."""
        github_id = raw_issue["id"]
        number = raw_issue["number"]

        issue = self.db.scalars(
            select(Issue).where(
                (Issue.repository_id == repository_id)
                & ((Issue.github_id == github_id) | (Issue.number == number))
            )
        ).first()

        created_at_dt = parse_datetime(raw_issue.get("created_at")) or utcnow()
        updated_at_dt = parse_datetime(raw_issue.get("updated_at"))
        closed_at_dt = parse_datetime(raw_issue.get("closed_at"))
        is_pr = "pull_request" in raw_issue

        if issue:
            issue.github_id = github_id
            issue.contributor_id = author_id
            issue.number = number
            issue.title = raw_issue.get("title", "")
            issue.body = raw_issue.get("body")
            issue.state = raw_issue.get("state", "open")
            issue.is_pull_request = is_pr
            issue.comments_count = raw_issue.get("comments", issue.comments_count)
            issue.created_at = created_at_dt
            issue.updated_at = updated_at_dt
            issue.closed_at = closed_at_dt
        else:
            issue = Issue(
                github_id=github_id,
                repository_id=repository_id,
                contributor_id=author_id,
                number=number,
                title=raw_issue.get("title", ""),
                body=raw_issue.get("body"),
                state=raw_issue.get("state", "open"),
                is_pull_request=is_pr,
                comments_count=raw_issue.get("comments", 0),
                created_at=created_at_dt,
                updated_at=updated_at_dt,
                closed_at=closed_at_dt,
            )
            self.db.add(issue)

        self.db.flush()
        return issue

    def upsert_comment(
        self,
        repository_id: int,
        raw_comment: Dict[str, Any],
        author_id: Optional[int],
        pull_request_id: Optional[int] = None,
        issue_id: Optional[int] = None,
        commit_id: Optional[int] = None,
        comment_type: str = "issue",
    ) -> Comment:
        """Idempotently insert or update a Comment record."""
        github_id = raw_comment["id"]

        comment = self.db.scalars(
            select(Comment).where(
                (Comment.repository_id == repository_id) & (Comment.github_id == github_id)
            )
        ).first()

        created_at_dt = parse_datetime(raw_comment.get("created_at")) or utcnow()
        updated_at_dt = parse_datetime(raw_comment.get("updated_at"))

        if comment:
            comment.contributor_id = author_id
            comment.pull_request_id = pull_request_id or comment.pull_request_id
            comment.issue_id = issue_id or comment.issue_id
            comment.commit_id = commit_id or comment.commit_id
            comment.comment_type = comment_type
            comment.body = raw_comment.get("body", "")
            comment.created_at = created_at_dt
            comment.updated_at = updated_at_dt
        else:
            comment = Comment(
                github_id=github_id,
                repository_id=repository_id,
                contributor_id=author_id,
                pull_request_id=pull_request_id,
                issue_id=issue_id,
                commit_id=commit_id,
                comment_type=comment_type,
                body=raw_comment.get("body", ""),
                created_at=created_at_dt,
                updated_at=updated_at_dt,
            )
            self.db.add(comment)

        self.db.flush()
        return comment

    def upsert_commit(
        self,
        repository_id: int,
        raw_commit: Dict[str, Any],
        author_id: Optional[int],
    ) -> Commit:
        """Idempotently insert or update a Commit record."""
        sha = raw_commit.get("sha", "")
        commit_obj = raw_commit.get("commit", {})

        commit = self.db.scalars(
            select(Commit).where(
                (Commit.repository_id == repository_id) & (Commit.sha == sha)
            )
        ).first()

        author_info = commit_obj.get("author", {}) if isinstance(commit_obj, dict) else {}
        committer_info = commit_obj.get("committer", {}) if isinstance(commit_obj, dict) else {}

        authored_at_dt = parse_datetime(author_info.get("date")) or utcnow()
        committed_at_dt = parse_datetime(committer_info.get("date")) or authored_at_dt

        stats = raw_commit.get("stats", {})
        additions = stats.get("additions", 0) if isinstance(stats, dict) else 0
        deletions = stats.get("deletions", 0) if isinstance(stats, dict) else 0
        total_changes = stats.get("total", additions + deletions) if isinstance(stats, dict) else (additions + deletions)

        message = commit_obj.get("message", "") if isinstance(commit_obj, dict) else raw_commit.get("message", "")

        if commit:
            commit.contributor_id = author_id or commit.contributor_id
            commit.message = message
            commit.authored_at = authored_at_dt
            commit.committed_at = committed_at_dt
            commit.additions = additions
            commit.deletions = deletions
            commit.total_changes = total_changes
        else:
            commit = Commit(
                repository_id=repository_id,
                contributor_id=author_id,
                sha=sha,
                message=message,
                authored_at=authored_at_dt,
                committed_at=committed_at_dt,
                additions=additions,
                deletions=deletions,
                total_changes=total_changes,
            )
            self.db.add(commit)

        self.db.flush()
        return commit

    def log_error(
        self,
        repository_id: Optional[int],
        analysis_run_id: Optional[int],
        stage: str,
        entity_type: Optional[str],
        entity_identifier: Optional[str],
        error_message: str,
        error_details: Optional[str] = None,
    ) -> IngestionError:
        """Record an ingestion failure in the ingestion_errors table."""
        err = IngestionError(
            repository_id=repository_id or 0,
            analysis_run_id=analysis_run_id,
            stage=stage,
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            error_message=error_message,
            error_details=error_details,
            occurred_at=utcnow(),
        )
        self.db.add(err)
        self.db.flush()
        return err

    # --------------------------------------------------------------------------
    # Main Ingestion Workflow
    # --------------------------------------------------------------------------

    def ingest_repository(
        self,
        owner: str,
        repo_name: str,
        max_pages: Optional[int] = None,
    ) -> AnalysisRun:
        """
        Execute full repository ingestion and idempotent persistence.

        Args:
            owner: Repository owner.
            repo_name: Repository name.
            max_pages: Optional maximum pages to pull per dataset.

        Returns:
            AnalysisRun: Completed analysis record.
        """
        run_uuid = str(uuid4())
        initiated_at = utcnow()

        # Step 1: Validate repository existence on GitHub
        try:
            raw_repo = self.github_client.get_repository(owner, repo_name)
        except GitHubNotFoundError:
            logger.warning("Repository %s/%s not found on GitHub.", owner, repo_name)
            raise
        except Exception as exc:
            logger.exception("Failed to connect to GitHub for repository %s/%s: %s", owner, repo_name, exc)
            raise

        # Step 2: Persist repository record
        repo = self.upsert_repository(raw_repo)

        # Step 3: Initialize AnalysisRun
        analysis_run = AnalysisRun(
            run_id=run_uuid,
            repository_id=repo.id,
            status="RUNNING",
            initiated_at=initiated_at,
        )
        self.db.add(analysis_run)
        self.db.commit()
        self.db.refresh(analysis_run)

        error_count = 0

        try:
            # ------------------------------------------------------------------
            # Stage 1: Ingest Contributors
            # ------------------------------------------------------------------
            logger.info("Ingesting contributors for %s...", repo.full_name)
            try:
                raw_contributors = self.github_client.get_contributors(owner, repo_name, max_pages=max_pages)
                for raw_c in raw_contributors:
                    self.upsert_user(raw_c)
            except Exception as exc:
                error_count += 1
                logger.warning("Error ingesting contributors: %s", exc)
                self.log_error(repo.id, analysis_run.id, "contributors", "contributor_list", None, str(exc))

            # ------------------------------------------------------------------
            # Stage 2: Ingest Pull Requests & Reviews
            # ------------------------------------------------------------------
            logger.info("Ingesting pull requests for %s...", repo.full_name)
            prs_count = 0
            pr_map: Dict[int, PullRequest] = {}  # number -> PullRequest
            try:
                raw_prs = self.github_client.get_pull_requests(owner, repo_name, state="all", max_pages=max_pages)
                for raw_pr in raw_prs:
                    author_user = self.upsert_user(raw_pr.get("user"))
                    author_id = author_user.id if author_user else None
                    pr = self.upsert_pull_request(repo.id, raw_pr, author_id)
                    pr_map[pr.number] = pr
                    prs_count += 1

                    # Fetch Reviews for PR
                    try:
                        raw_reviews = self.github_client.get_reviews(owner, repo_name, pr.number, max_pages=max_pages)
                        for raw_rev in raw_reviews:
                            rev_user = self.upsert_user(raw_rev.get("user"))
                            rev_user_id = rev_user.id if rev_user else None
                            self.upsert_review(pr.id, raw_rev, rev_user_id)
                    except Exception as rev_exc:
                        error_count += 1
                        self.log_error(repo.id, analysis_run.id, "reviews", "pull_request_review", str(pr.number), str(rev_exc))
            except Exception as exc:
                error_count += 1
                logger.warning("Error ingesting pull requests: %s", exc)
                self.log_error(repo.id, analysis_run.id, "pull_requests", "pr_list", None, str(exc))

            # ------------------------------------------------------------------
            # Stage 3: Ingest Issues
            # ------------------------------------------------------------------
            logger.info("Ingesting issues for %s...", repo.full_name)
            issues_count = 0
            issue_map: Dict[int, Issue] = {}  # number -> Issue
            try:
                raw_issues = self.github_client.get_issues(owner, repo_name, state="all", max_pages=max_pages)
                for raw_issue in raw_issues:
                    author_user = self.upsert_user(raw_issue.get("user"))
                    author_id = author_user.id if author_user else None
                    issue = self.upsert_issue(repo.id, raw_issue, author_id)
                    issue_map[issue.number] = issue
                    issues_count += 1
            except Exception as exc:
                error_count += 1
                logger.warning("Error ingesting issues: %s", exc)
                self.log_error(repo.id, analysis_run.id, "issues", "issue_list", None, str(exc))

            # ------------------------------------------------------------------
            # Stage 4: Ingest Comments
            # ------------------------------------------------------------------
            logger.info("Ingesting comments for %s...", repo.full_name)
            try:
                raw_comments = self.github_client.get_comments(owner, repo_name, max_pages=max_pages)
                for raw_comment in raw_comments:
                    author_user = self.upsert_user(raw_comment.get("user"))
                    author_id = author_user.id if author_user else None

                    # Extract issue number from issue_url if present
                    issue_url = raw_comment.get("issue_url", "")
                    issue_num = None
                    if "/issues/" in issue_url:
                        try:
                            issue_num = int(issue_url.split("/issues/")[-1])
                        except ValueError:
                            issue_num = None

                    pr_id = pr_map[issue_num].id if issue_num and issue_num in pr_map else None
                    iss_id = issue_map[issue_num].id if issue_num and issue_num in issue_map else None

                    self.upsert_comment(
                        repo.id,
                        raw_comment,
                        author_id,
                        pull_request_id=pr_id,
                        issue_id=iss_id,
                        comment_type="issue",
                    )
            except Exception as exc:
                error_count += 1
                logger.warning("Error ingesting comments: %s", exc)
                self.log_error(repo.id, analysis_run.id, "comments", "comment_list", None, str(exc))

            # ------------------------------------------------------------------
            # Stage 5: Ingest Commits
            # ------------------------------------------------------------------
            logger.info("Ingesting commits for %s...", repo.full_name)
            commits_count = 0
            try:
                raw_commits = self.github_client.get_commits(owner, repo_name, max_pages=max_pages)
                for raw_commit in raw_commits:
                    author_user = self.upsert_user(raw_commit.get("author"))
                    author_id = author_user.id if author_user else None
                    self.upsert_commit(repo.id, raw_commit, author_id)
                    commits_count += 1
            except Exception as exc:
                error_count += 1
                logger.warning("Error ingesting commits: %s", exc)
                self.log_error(repo.id, analysis_run.id, "commits", "commit_list", None, str(exc))

            # ------------------------------------------------------------------
            # Finalize Analysis Run Counts & Status
            # ------------------------------------------------------------------
            completed_at = utcnow()
            duration = (completed_at - initiated_at).total_seconds()

            # Query real count of distinct contributors associated with this repo
            distinct_contributors = self.db.scalar(
                select(func.count(func.distinct(PullRequest.contributor_id))).where(
                    PullRequest.repository_id == repo.id
                )
            ) or 0

            analysis_run.total_prs_ingested = prs_count
            analysis_run.total_commits_ingested = commits_count
            analysis_run.total_issues_ingested = issues_count
            analysis_run.total_contributors_ingested = distinct_contributors
            analysis_run.status = "PARTIALLY_COMPLETED" if error_count > 0 else "COMPLETED"
            analysis_run.completed_at = completed_at
            analysis_run.duration_seconds = duration

            self.db.commit()
            self.db.refresh(analysis_run)
            return analysis_run

        except Exception as fatal_exc:
            self.db.rollback()
            logger.exception("Fatal error during analysis of %s/%s: %s", owner, repo_name, fatal_exc)

            # Update run to FAILED
            failed_run = self.db.scalars(
                select(AnalysisRun).where(AnalysisRun.id == analysis_run.id)
            ).first()
            if failed_run:
                failed_run.status = "FAILED"
                failed_run.error_message = str(fatal_exc)
                failed_run.completed_at = utcnow()
                self.db.commit()
                self.db.refresh(failed_run)
                return failed_run
            raise
