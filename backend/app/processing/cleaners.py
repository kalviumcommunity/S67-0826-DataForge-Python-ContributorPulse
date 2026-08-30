"""Dataset-specific cleaning, validation, and missing-value strategies."""

import re
from typing import Any, Dict, List, Optional, Tuple
from backend.app.processing.normalizers import normalize_text, normalize_timestamp

SHA_REGEX = re.compile(r"^[0-9a-fA-F]{7,40}$")


def clean_user_data(raw_user: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean and validate a User / Contributor record.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    github_id = raw_user.get("id") or raw_user.get("github_id")
    if not github_id or not isinstance(github_id, int) or github_id <= 0:
        errors.append(f"Invalid user github_id: {github_id}")
        return None, errors, missing_handled

    login = normalize_text(raw_user.get("login"))
    if not login:
        errors.append("User login is missing or blank")
        return None, errors, missing_handled

    # Normalize user_type
    user_type = normalize_text(raw_user.get("type") or raw_user.get("user_type"), default="User")
    if user_type != raw_user.get("user_type"):
        missing_handled += 1

    # Check bot status
    is_bot = bool(
        raw_user.get("is_bot")
        or (user_type and user_type.lower() == "bot")
        or "[bot]" in login.lower()
    )

    cleaned = {
        "github_id": github_id,
        "login": login,
        "name": normalize_text(raw_user.get("name")),
        "email": normalize_text(raw_user.get("email")),
        "avatar_url": normalize_text(raw_user.get("avatar_url")),
        "html_url": normalize_text(raw_user.get("html_url")),
        "user_type": user_type,
        "is_bot": is_bot,
    }

    return cleaned, errors, missing_handled


def clean_pull_request_data(
    raw_pr: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean, validate, and impute missing values for a Pull Request record.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    github_id = raw_pr.get("id") or raw_pr.get("github_id")
    if not github_id or not isinstance(github_id, int) or github_id <= 0:
        errors.append(f"Invalid PR github_id: {github_id}")
        return None, errors, missing_handled

    number = raw_pr.get("number")
    if not number or not isinstance(number, int) or number <= 0:
        errors.append(f"Invalid PR number: {number}")
        return None, errors, missing_handled

    created_at = normalize_timestamp(raw_pr.get("created_at"))
    if not created_at:
        errors.append("PR missing required created_at timestamp")
        return None, errors, missing_handled

    # Title imputation
    title = normalize_text(raw_pr.get("title"))
    if not title:
        title = "(No title)"
        missing_handled += 1

    # State normalization
    state = str(raw_pr.get("state", "open")).lower()
    if state not in ("open", "closed"):
        state = "open"
        missing_handled += 1

    merged_at = normalize_timestamp(raw_pr.get("merged_at"))
    closed_at = normalize_timestamp(raw_pr.get("closed_at"))
    updated_at = normalize_timestamp(raw_pr.get("updated_at"))

    is_merged = bool(merged_at or raw_pr.get("merged", False) or raw_pr.get("is_merged", False))

    # Metric non-negative constraints
    additions = max(0, int(raw_pr.get("additions") or 0))
    deletions = max(0, int(raw_pr.get("deletions") or 0))
    changed_files = max(0, int(raw_pr.get("changed_files") or 0))
    comments_count = max(0, int(raw_pr.get("comments") or raw_pr.get("comments_count") or 0))
    review_comments_count = max(
        0, int(raw_pr.get("review_comments") or raw_pr.get("review_comments_count") or 0)
    )

    author_assoc = normalize_text(raw_pr.get("author_association"), default="NONE")
    is_first_time = author_assoc == "FIRST_TIME_CONTRIBUTOR" or bool(
        raw_pr.get("is_first_time_contributor", False)
    )

    cleaned = {
        "github_id": github_id,
        "number": number,
        "title": title,
        "body": normalize_text(raw_pr.get("body")),
        "state": state,
        "is_draft": bool(raw_pr.get("draft") or raw_pr.get("is_draft", False)),
        "is_merged": is_merged,
        "is_first_time_contributor": is_first_time,
        "author_association": author_assoc,
        "created_at": created_at,
        "updated_at": updated_at,
        "closed_at": closed_at,
        "merged_at": merged_at,
        "merge_commit_sha": normalize_text(raw_pr.get("merge_commit_sha")),
        "head_sha": normalize_text(
            raw_pr.get("head", {}).get("sha")
            if isinstance(raw_pr.get("head"), dict)
            else raw_pr.get("head_sha")
        ),
        "base_branch": normalize_text(
            raw_pr.get("base", {}).get("ref")
            if isinstance(raw_pr.get("base"), dict)
            else raw_pr.get("base_branch")
        ),
        "additions": additions,
        "deletions": deletions,
        "changed_files": changed_files,
        "comments_count": comments_count,
        "review_comments_count": review_comments_count,
    }

    return cleaned, errors, missing_handled


def clean_issue_data(raw_issue: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean, validate, and normalize Issue records.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    github_id = raw_issue.get("id") or raw_issue.get("github_id")
    if not github_id or not isinstance(github_id, int) or github_id <= 0:
        errors.append(f"Invalid issue github_id: {github_id}")
        return None, errors, missing_handled

    number = raw_issue.get("number")
    if not number or not isinstance(number, int) or number <= 0:
        errors.append(f"Invalid issue number: {number}")
        return None, errors, missing_handled

    created_at = normalize_timestamp(raw_issue.get("created_at"))
    if not created_at:
        errors.append("Issue missing required created_at timestamp")
        return None, errors, missing_handled

    title = normalize_text(raw_issue.get("title"))
    if not title:
        title = "(No title)"
        missing_handled += 1

    state = str(raw_issue.get("state", "open")).lower()
    if state not in ("open", "closed"):
        state = "open"
        missing_handled += 1

    is_pr = bool("pull_request" in raw_issue or raw_issue.get("is_pull_request", False))
    comments_count = max(0, int(raw_issue.get("comments") or raw_issue.get("comments_count") or 0))

    cleaned = {
        "github_id": github_id,
        "number": number,
        "title": title,
        "body": normalize_text(raw_issue.get("body")),
        "state": state,
        "is_pull_request": is_pr,
        "comments_count": comments_count,
        "created_at": created_at,
        "updated_at": normalize_timestamp(raw_issue.get("updated_at")),
        "closed_at": normalize_timestamp(raw_issue.get("closed_at")),
    }

    return cleaned, errors, missing_handled


def clean_review_data(
    raw_review: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean, validate, and normalize PR Review records.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    github_id = raw_review.get("id") or raw_review.get("github_id")
    if not github_id or not isinstance(github_id, int) or github_id <= 0:
        errors.append(f"Invalid review github_id: {github_id}")
        return None, errors, missing_handled

    submitted_at = normalize_timestamp(
        raw_review.get("submitted_at") or raw_review.get("created_at")
    )
    if not submitted_at:
        errors.append("Review missing required submitted_at timestamp")
        return None, errors, missing_handled

    raw_state = str(raw_review.get("state", "COMMENTED")).upper()
    valid_states = {"APPROVED", "CHANGES_REQUESTED", "COMMENTED", "DISMISSED", "PENDING"}
    if raw_state not in valid_states:
        state = "COMMENTED"
        missing_handled += 1
    else:
        state = raw_state

    cleaned = {
        "github_id": github_id,
        "state": state,
        "body": normalize_text(raw_review.get("body")),
        "submitted_at": submitted_at,
    }

    return cleaned, errors, missing_handled


def clean_comment_data(
    raw_comment: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean, validate, and normalize Issue/PR Comment records.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    github_id = raw_comment.get("id") or raw_comment.get("github_id")
    if not github_id or not isinstance(github_id, int) or github_id <= 0:
        errors.append(f"Invalid comment github_id: {github_id}")
        return None, errors, missing_handled

    created_at = normalize_timestamp(raw_comment.get("created_at"))
    if not created_at:
        errors.append("Comment missing required created_at timestamp")
        return None, errors, missing_handled

    body = normalize_text(raw_comment.get("body"))
    if not body:
        body = "(empty comment)"
        missing_handled += 1

    comment_type = normalize_text(raw_comment.get("comment_type"), default="issue")

    cleaned = {
        "github_id": github_id,
        "body": body,
        "comment_type": comment_type,
        "created_at": created_at,
        "updated_at": normalize_timestamp(raw_comment.get("updated_at")),
    }

    return cleaned, errors, missing_handled


def clean_commit_data(
    raw_commit: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], List[str], int]:
    """
    Clean, validate, and normalize Commit records.

    Returns:
        Tuple[cleaned_record_or_None, validation_errors_list, missing_values_handled_count]
    """
    errors: List[str] = []
    missing_handled = 0

    sha = str(raw_commit.get("sha", "")).strip()
    if not sha or not SHA_REGEX.match(sha):
        errors.append(f"Invalid commit sha format: {sha}")
        return None, errors, missing_handled

    commit_obj = raw_commit.get("commit")
    author_date = None
    committer_date = None
    if isinstance(commit_obj, dict):
        author_info = commit_obj.get("author")
        if isinstance(author_info, dict):
            author_date = author_info.get("date")
        committer_info = commit_obj.get("committer")
        if isinstance(committer_info, dict):
            committer_date = committer_info.get("date")
        raw_msg = commit_obj.get("message")
    else:
        raw_msg = raw_commit.get("message")

    authored_at = (
        normalize_timestamp(author_date)
        or normalize_timestamp(raw_commit.get("authored_at"))
    )
    committed_at = (
        normalize_timestamp(committer_date)
        or normalize_timestamp(raw_commit.get("committed_at"))
        or authored_at
    )

    if not authored_at:
        authored_at = committed_at
        missing_handled += 1

    message = normalize_text(raw_msg)
    if not message:
        message = "(no commit message)"
        missing_handled += 1

    stats = raw_commit.get("stats", {})
    additions = max(0, int(stats.get("additions") or raw_commit.get("additions") or 0))
    deletions = max(0, int(stats.get("deletions") or raw_commit.get("deletions") or 0))
    total_changes = max(
        0,
        int(
            stats.get("total")
            or raw_commit.get("total_changes")
            or (additions + deletions)
        ),
    )

    cleaned = {
        "sha": sha,
        "message": message,
        "authored_at": authored_at,
        "committed_at": committed_at,
        "additions": additions,
        "deletions": deletions,
        "total_changes": total_changes,
    }

    return cleaned, errors, missing_handled
