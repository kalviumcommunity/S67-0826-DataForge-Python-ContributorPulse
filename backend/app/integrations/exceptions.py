"""Custom typed exceptions for GitHub REST API client."""

from typing import Any, Dict, Optional


class GitHubAPIError(Exception):
    """Base exception for all GitHub API client errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[HTTP {self.status_code}] {self.message}"
        return self.message


class GitHubAuthenticationError(GitHubAPIError):
    """Raised when GitHub returns 401 Unauthorized (invalid or expired token)."""
    pass


class GitHubForbiddenError(GitHubAPIError):
    """Raised when GitHub returns 403 Forbidden (insufficient permissions)."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """Raised when GitHub rate limit is exceeded (HTTP 403 Rate Limit or HTTP 429)."""

    def __init__(
        self,
        message: str,
        status_code: int = 429,
        response_body: Optional[Any] = None,
        reset_timestamp: Optional[int] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(message, status_code, response_body)
        self.reset_timestamp = reset_timestamp
        self.retry_after = retry_after


class GitHubNotFoundError(GitHubAPIError):
    """Raised when requested GitHub repository or resource is not found (HTTP 404)."""
    pass


class GitHubValidationError(GitHubAPIError):
    """Raised when GitHub rejects input parameters with 422 Unprocessable Entity."""
    pass


class GitHubTimeoutError(GitHubAPIError):
    """Raised when an HTTP request to GitHub times out."""
    pass


class GitHubServerError(GitHubAPIError):
    """Raised when GitHub returns 5xx server-side errors."""
    pass
