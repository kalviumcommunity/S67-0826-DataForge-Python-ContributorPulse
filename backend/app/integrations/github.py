"""Production-grade GitHub REST API client with pagination, rate limiting, and backoff."""

import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from fastapi import Depends

from backend.app.core.config import Settings, get_settings
from backend.app.integrations.exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubForbiddenError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubServerError,
    GitHubTimeoutError,
    GitHubValidationError,
)

logger = logging.getLogger("contributor_pulse.github_client")


class GitHubClient:
    """Production GitHub REST API client supporting auth, pagination, retries, and rate limit handling."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        timeout: float = 15.0,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._external_client = client is not None
        self.client = client or httpx.Client(timeout=self.timeout)

    def _get_headers(self) -> Dict[str, str]:
        """Construct standard GitHub API headers with authorization when token is set."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "ContributorPulse/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _handle_response_error(self, response: httpx.Response) -> None:
        """Inspect HTTP response and raise appropriate typed domain exception."""
        status_code = response.status_code
        try:
            body = response.json()
            message = body.get("message", response.text) if isinstance(body, dict) else str(body)
        except Exception:
            body = response.text
            message = response.text or f"HTTP error {status_code}"

        # 401 Unauthorized
        if status_code == 401:
            raise GitHubAuthenticationError("GitHub authentication failed: Invalid or expired token.", status_code, body)

        # 403 Forbidden / Rate limit
        if status_code == 403:
            remaining = response.headers.get("x-ratelimit-remaining")
            reset_ts = response.headers.get("x-ratelimit-reset")
            retry_after = response.headers.get("retry-after")

            if remaining == "0" or "rate limit" in str(message).lower() or "secondary rate limit" in str(message).lower():
                reset_int = int(reset_ts) if reset_ts and reset_ts.isdigit() else None
                retry_int = int(retry_after) if retry_after and retry_after.isdigit() else None
                raise GitHubRateLimitError(
                    f"GitHub rate limit exceeded: {message}",
                    status_code=403,
                    response_body=body,
                    reset_timestamp=reset_int,
                    retry_after=retry_int,
                )
            raise GitHubForbiddenError(f"GitHub access forbidden: {message}", status_code, body)

        # 404 Not Found
        if status_code == 404:
            raise GitHubNotFoundError(f"GitHub resource not found: {message}", status_code, body)

        # 422 Unprocessable Entity
        if status_code == 422:
            raise GitHubValidationError(f"GitHub validation error: {message}", status_code, body)

        # 429 Too Many Requests
        if status_code == 429:
            retry_after = response.headers.get("retry-after")
            retry_int = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise GitHubRateLimitError(
                f"GitHub rate limit exceeded: {message}",
                status_code=429,
                response_body=body,
                retry_after=retry_int,
            )

        # 5xx Server Error
        if status_code >= 500:
            raise GitHubServerError(f"GitHub server error: {message}", status_code, body)

        # Generic API Error
        raise GitHubAPIError(f"GitHub API request failed: {message}", status_code, body)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """
        Execute an HTTP request against GitHub REST API with exponential backoff retries.

        Args:
            method: HTTP verb ("GET", "POST", etc.).
            endpoint: API path starting with "/" or full URL.
            params: Query parameters.

        Returns:
            httpx.Response: Successful HTTP response.
        """
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                )

                if response.is_success:
                    return response

                # Check if retryable server error (500, 502, 503, 504)
                if response.status_code in (500, 502, 503, 504) and attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "Transient GitHub %d error. Retrying in %.2fs (attempt %d/%d)...",
                        response.status_code,
                        sleep_time,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue

                self._handle_response_error(response)

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    sleep_time = self.backoff_factor * (2**attempt)
                    logger.warning(
                        "Network error (%s) contacting GitHub. Retrying in %.2fs (attempt %d/%d)...",
                        exc.__class__.__name__,
                        sleep_time,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(sleep_time)
                    continue
                raise GitHubTimeoutError(f"GitHub request timed out or network failed after {self.max_retries} retries: {exc}") from exc

        if last_exception:
            raise GitHubAPIError(f"GitHub request failed: {last_exception}") from last_exception
        raise GitHubAPIError("GitHub request failed with unknown error.")

    def _paginate(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all pages of a paginated GitHub endpoint.

        Args:
            endpoint: API endpoint path.
            params: Initial query parameters.
            max_pages: Maximum number of pages to retrieve (None for all).

        Returns:
            List[Dict[str, Any]]: Consolidated items across all retrieved pages.
        """
        request_params = dict(params or {})
        request_params.setdefault("per_page", 100)
        request_params.setdefault("page", 1)

        all_items: List[Dict[str, Any]] = []
        page = request_params["page"]
        pages_retrieved = 0

        while True:
            request_params["page"] = page
            response = self._request("GET", endpoint, params=request_params)
            data = response.json()

            if not isinstance(data, list) or not data:
                break

            all_items.extend(data)
            pages_retrieved += 1

            if max_pages is not None and pages_retrieved >= max_pages:
                break

            # If fewer items than per_page returned, this was the final page
            if len(data) < request_params["per_page"]:
                break

            page += 1

        return all_items

    # --------------------------------------------------------------------------
    # Public API Methods
    # --------------------------------------------------------------------------

    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """Fetch repository metadata."""
        endpoint = f"/repos/{owner}/{repo}"
        response = self._request("GET", endpoint)
        return response.json()

    def get_contributors(
        self, owner: str, repo: str, max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Fetch repository contributors list."""
        endpoint = f"/repos/{owner}/{repo}/contributors"
        return self._paginate(endpoint, max_pages=max_pages)

    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch pull requests for a repository."""
        endpoint = f"/repos/{owner}/{repo}/pulls"
        return self._paginate(endpoint, params={"state": state}, max_pages=max_pages)

    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "all",
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch repository issues (includes pull requests by GitHub REST API design)."""
        endpoint = f"/repos/{owner}/{repo}/issues"
        return self._paginate(endpoint, params={"state": state}, max_pages=max_pages)

    def get_reviews(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch reviews for a specific pull request."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        return self._paginate(endpoint, max_pages=max_pages)

    def get_comments(
        self,
        owner: str,
        repo: str,
        issue_number: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch issue/PR comments (or all repo issue comments if issue_number is None)."""
        if issue_number is not None:
            endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        else:
            endpoint = f"/repos/{owner}/{repo}/issues/comments"
        return self._paginate(endpoint, max_pages=max_pages)

    def get_commits(
        self,
        owner: str,
        repo: str,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch commit history for a repository."""
        endpoint = f"/repos/{owner}/{repo}/commits"
        return self._paginate(endpoint, max_pages=max_pages)

    def get_contributor_commits(
        self,
        owner: str,
        repo: str,
        author: str,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch commits made by a specific contributor."""
        endpoint = f"/repos/{owner}/{repo}/commits"
        return self._paginate(endpoint, params={"author": author}, max_pages=max_pages)

    def get_commit_activity(
        self,
        owner: str,
        repo: str,
    ) -> List[Dict[str, Any]]:
        """Fetch weekly commit activity statistics."""
        endpoint = f"/repos/{owner}/{repo}/stats/commit_activity"
        response = self._request("GET", endpoint)
        data = response.json()
        return data if isinstance(data, list) else []

    def close(self) -> None:
        """Close the underlying HTTP client if internally managed."""
        if not self._external_client:
            self.client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __repr__(self) -> str:
        masked_tok = "****" if self.token else "None"
        return f"GitHubClient(base_url='{self.base_url}', token={masked_tok}, timeout={self.timeout})"


def get_github_client(
    settings: Settings = Depends(get_settings),
) -> GitHubClient:
    """FastAPI dependency provider for GitHubClient."""
    return GitHubClient(token=settings.GITHUB_TOKEN)
