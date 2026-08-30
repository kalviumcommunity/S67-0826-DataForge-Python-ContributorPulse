"""Bridge connecting Streamlit frontend calls to the ContributorPulse FastAPI backend."""

import logging
from typing import Any, Dict, List, Optional
from api_client import BackendAPIClient

logger = logging.getLogger("contributor_pulse.frontend_bridge")

_client = BackendAPIClient()


def get_repository(owner: str, repository: str) -> Optional[Dict[str, Any]]:
    """Retrieve repository details from backend service."""
    return _client.get_repository(owner, repository)


def get_contributors(owner: str, repository: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve contributor journeys from backend service."""
    res = _client.get_contributors(owner, repository, per_page=100)
    if isinstance(res, dict) and "items" in res:
        return res["items"]
    return None


def get_commit_activity(owner: str, repository: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve activity and timeline from backend service."""
    res = _client.get_review_timeline(owner, repository)
    if isinstance(res, dict) and "timeline" in res:
        return res["timeline"]
    return []


def get_pull_requests(owner: str, repository: str) -> Optional[Dict[str, Any]]:
    """Retrieve pull request merge statistics from backend service."""
    return _client.get_merge_stats(owner, repository)


def get_commits(owner: str, repository: str) -> Optional[Dict[str, Any]]:
    """Retrieve repository commit summary from backend service."""
    return _client.get_repository_summary(owner, repository)