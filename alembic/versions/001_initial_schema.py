"""Initial normalized database schema for ContributorPulse.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-08-30 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --------------------------------------------------------------------------
    # 1. Repositories Table
    # --------------------------------------------------------------------------
    op.create_table(
        "repositories",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("primary_language", sa.String(length=100), nullable=True),
        sa.Column("stars_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("forks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("default_branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_fork", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_repositories_github_id", "repositories", ["github_id"], unique=True)
    op.create_index("ix_repositories_owner", "repositories", ["owner"])
    op.create_index("ix_repositories_name", "repositories", ["name"])
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"], unique=True)

    # --------------------------------------------------------------------------
    # 2. Users Table
    # --------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("html_url", sa.String(length=1024), nullable=True),
        sa.Column("user_type", sa.String(length=50), nullable=False, server_default="User"),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_github_id", "users", ["github_id"], unique=True)
    op.create_index("ix_users_login", "users", ["login"], unique=True)
    op.create_index("ix_users_email", "users", ["email"])

    # --------------------------------------------------------------------------
    # 3. Analysis Runs Table
    # --------------------------------------------------------------------------
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=100), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("initiated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("total_prs_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_commits_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_issues_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_contributors_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_analysis_runs_run_id", "analysis_runs", ["run_id"], unique=True)
    op.create_index("ix_analysis_runs_repository_id", "analysis_runs", ["repository_id"])
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])
    op.create_index("ix_analysis_runs_initiated_at", "analysis_runs", ["initiated_at"])

    # --------------------------------------------------------------------------
    # 4. Pull Requests Table
    # --------------------------------------------------------------------------
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_first_time_contributor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("author_association", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merge_commit_sha", sa.String(length=100), nullable=True),
        sa.Column("head_sha", sa.String(length=100), nullable=True),
        sa.Column("base_branch", sa.String(length=100), nullable=True),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changed_files", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("repository_id", "github_id", name="uq_pull_requests_repo_github_id"),
        sa.UniqueConstraint("repository_id", "number", name="uq_pull_requests_repo_number"),
    )
    op.create_index("ix_pull_requests_github_id", "pull_requests", ["github_id"])
    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"])
    op.create_index("ix_pull_requests_contributor_id", "pull_requests", ["contributor_id"])
    op.create_index("ix_pull_requests_number", "pull_requests", ["number"])
    op.create_index("ix_pull_requests_state", "pull_requests", ["state"])
    op.create_index("ix_pull_requests_is_merged", "pull_requests", ["is_merged"])
    op.create_index("ix_pull_requests_is_first_time_contributor", "pull_requests", ["is_first_time_contributor"])
    op.create_index("ix_pull_requests_created_at", "pull_requests", ["created_at"])
    op.create_index("ix_pull_requests_merged_at", "pull_requests", ["merged_at"])

    # --------------------------------------------------------------------------
    # 5. Issues Table
    # --------------------------------------------------------------------------
    op.create_table(
        "issues",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1024), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("is_pull_request", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("repository_id", "github_id", name="uq_issues_repo_github_id"),
        sa.UniqueConstraint("repository_id", "number", name="uq_issues_repo_number"),
    )
    op.create_index("ix_issues_github_id", "issues", ["github_id"])
    op.create_index("ix_issues_repository_id", "issues", ["repository_id"])
    op.create_index("ix_issues_contributor_id", "issues", ["contributor_id"])
    op.create_index("ix_issues_number", "issues", ["number"])
    op.create_index("ix_issues_state", "issues", ["state"])
    op.create_index("ix_issues_created_at", "issues", ["created_at"])

    # --------------------------------------------------------------------------
    # 6. Reviews Table
    # --------------------------------------------------------------------------
    op.create_table(
        "reviews",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("pull_request_id", sa.BigInteger(), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("state", sa.String(length=50), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("pull_request_id", "github_id", name="uq_reviews_pr_github_id"),
    )
    op.create_index("ix_reviews_github_id", "reviews", ["github_id"])
    op.create_index("ix_reviews_pull_request_id", "reviews", ["pull_request_id"])
    op.create_index("ix_reviews_contributor_id", "reviews", ["contributor_id"])
    op.create_index("ix_reviews_state", "reviews", ["state"])
    op.create_index("ix_reviews_submitted_at", "reviews", ["submitted_at"])

    # --------------------------------------------------------------------------
    # 7. Commits Table
    # --------------------------------------------------------------------------
    op.create_table(
        "commits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sha", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("additions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_changes", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("repository_id", "sha", name="uq_commits_repo_sha"),
    )
    op.create_index("ix_commits_repository_id", "commits", ["repository_id"])
    op.create_index("ix_commits_contributor_id", "commits", ["contributor_id"])
    op.create_index("ix_commits_sha", "commits", ["sha"])
    op.create_index("ix_commits_authored_at", "commits", ["authored_at"])
    op.create_index("ix_commits_committed_at", "commits", ["committed_at"])

    # --------------------------------------------------------------------------
    # 8. Comments Table
    # --------------------------------------------------------------------------
    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pull_request_id", sa.BigInteger(), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("issue_id", sa.BigInteger(), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=True),
        sa.Column("commit_id", sa.BigInteger(), sa.ForeignKey("commits.id", ondelete="CASCADE"), nullable=True),
        sa.Column("comment_type", sa.String(length=50), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("repository_id", "github_id", name="uq_comments_repo_github_id"),
    )
    op.create_index("ix_comments_github_id", "comments", ["github_id"])
    op.create_index("ix_comments_repository_id", "comments", ["repository_id"])
    op.create_index("ix_comments_contributor_id", "comments", ["contributor_id"])
    op.create_index("ix_comments_pull_request_id", "comments", ["pull_request_id"])
    op.create_index("ix_comments_issue_id", "comments", ["issue_id"])
    op.create_index("ix_comments_commit_id", "comments", ["commit_id"])
    op.create_index("ix_comments_comment_type", "comments", ["comment_type"])
    op.create_index("ix_comments_created_at", "comments", ["created_at"])

    # --------------------------------------------------------------------------
    # 9. Contributor Features Table
    # --------------------------------------------------------------------------
    op.create_table(
        "contributor_features",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contributor_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_run_id", sa.BigInteger(), sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_contribution_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_pr_id", sa.BigInteger(), sa.ForeignKey("pull_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_pr_merged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("first_pr_review_duration_seconds", sa.Float(), nullable=True),
        sa.Column("first_pr_merge_duration_seconds", sa.Float(), nullable=True),
        sa.Column("first_response_time_seconds", sa.Float(), nullable=True),
        sa.Column("total_prs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("merged_prs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_commits", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_reviews", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_comments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_first_time_contributor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_retained_30d", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_retained_60d", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_retained_90d", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("retention_status", sa.String(length=50), nullable=False, server_default="onboarding"),
        sa.Column("churn_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("churn_risk_level", sa.String(length=50), nullable=False, server_default="low"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("repository_id", "contributor_id", name="uq_contributor_features_repo_contributor"),
    )
    op.create_index("ix_contributor_features_repository_id", "contributor_features", ["repository_id"])
    op.create_index("ix_contributor_features_contributor_id", "contributor_features", ["contributor_id"])
    op.create_index("ix_contributor_features_analysis_run_id", "contributor_features", ["analysis_run_id"])
    op.create_index("ix_contributor_features_first_contribution_at", "contributor_features", ["first_contribution_at"])
    op.create_index("ix_contributor_features_is_first_time_contributor", "contributor_features", ["is_first_time_contributor"])
    op.create_index("ix_contributor_features_is_retained_30d", "contributor_features", ["is_retained_30d"])
    op.create_index("ix_contributor_features_is_retained_60d", "contributor_features", ["is_retained_60d"])
    op.create_index("ix_contributor_features_is_retained_90d", "contributor_features", ["is_retained_90d"])
    op.create_index("ix_contributor_features_retention_status", "contributor_features", ["retention_status"])
    op.create_index("ix_contributor_features_last_active_at", "contributor_features", ["last_active_at"])

    # --------------------------------------------------------------------------
    # 10. Ingestion Errors Table
    # --------------------------------------------------------------------------
    op.create_table(
        "ingestion_errors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("repository_id", sa.BigInteger(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("analysis_run_id", sa.BigInteger(), sa.ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=True),
        sa.Column("entity_identifier", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ingestion_errors_repository_id", "ingestion_errors", ["repository_id"])
    op.create_index("ix_ingestion_errors_analysis_run_id", "ingestion_errors", ["analysis_run_id"])
    op.create_index("ix_ingestion_errors_stage", "ingestion_errors", ["stage"])
    op.create_index("ix_ingestion_errors_occurred_at", "ingestion_errors", ["occurred_at"])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("ingestion_errors")
    op.drop_table("contributor_features")
    op.drop_table("comments")
    op.drop_table("commits")
    op.drop_table("reviews")
    op.drop_table("issues")
    op.drop_table("pull_requests")
    op.drop_table("analysis_runs")
    op.drop_table("users")
    op.drop_table("repositories")
