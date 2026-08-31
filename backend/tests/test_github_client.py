"""Comprehensive deterministic unit tests for GitHub REST API client."""

import httpx
import pytest

from backend.app.core.config import Settings
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
from backend.app.integrations.github import GitHubClient, get_github_client


def test_auth_header_and_repr() -> None:
    """Test authorization header generation and secret safety in repr."""
    # With token
    client_with_tok = GitHubClient(token="test_secret_token_123456789")
    headers = client_with_tok._get_headers()
    assert headers["Authorization"] == "Bearer test_secret_token_123456789"
    assert "test_secret_token_123456789" not in repr(client_with_tok)
    assert "****" in repr(client_with_tok)

    # Without token
    client_no_tok = GitHubClient(token=None)
    headers_no_tok = client_no_tok._get_headers()
    assert "Authorization" not in headers_no_tok
    assert "token=None" in repr(client_no_tok)


def test_github_api_error_str() -> None:
    """Test string representation of GitHubAPIError with and without status code."""
    err_with_code = GitHubAPIError("Bad request", status_code=400)
    assert str(err_with_code) == "[HTTP 400] Bad request"

    err_no_code = GitHubAPIError("Network failed")
    assert str(err_no_code) == "Network failed"


def test_get_repository_success() -> None:
    """Test successful repository metadata retrieval."""
    mock_payload = {
        "id": 12345,
        "name": "ContributorPulse",
        "full_name": "org/ContributorPulse",
        "stargazers_count": 42,
        "owner": {"login": "org"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/repos/org/ContributorPulse"
        return httpx.Response(200, json=mock_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        repo = client.get_repository("org", "ContributorPulse")
        assert repo["name"] == "ContributorPulse"
        assert repo["stargazers_count"] == 42


def test_pagination_multiple_pages() -> None:
    """Test paginated responses across multiple pages."""

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", 1))
        if page == 1:
            return httpx.Response(200, json=[{"id": i} for i in range(100)])
        elif page == 2:
            return httpx.Response(200, json=[{"id": i + 100} for i in range(25)])
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        contributors = client.get_contributors("org", "repo")
        assert len(contributors) == 125
        assert contributors[0]["id"] == 0
        assert contributors[124]["id"] == 124


def test_pagination_max_pages_limit() -> None:
    """Test pagination honors max_pages parameter."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}])

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        items = client.get_contributors("org", "repo", max_pages=1)
        assert len(items) == 2


def test_transient_failure_retry_and_recovery() -> None:
    """Test transient 500 error retries and succeeds on next attempt."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"message": "Internal Server Error"})
        return httpx.Response(200, json={"id": 1, "name": "recovered-repo"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client, max_retries=2, backoff_factor=0.01)
        repo = client.get_repository("org", "recovered-repo")
        assert repo["name"] == "recovered-repo"
        assert attempts == 2


def test_transient_failure_max_retries_exceeded() -> None:
    """Test persistent 503 error raises GitHubServerError after retries."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "Service Unavailable"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client, max_retries=2, backoff_factor=0.01)
        with pytest.raises(GitHubServerError) as exc:
            client.get_repository("org", "failed-repo")
        assert exc.value.status_code == 503


def test_request_timeout_behavior() -> None:
    """Test network timeout triggers retries and raises GitHubTimeoutError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client, max_retries=1, backoff_factor=0.01)
        with pytest.raises(GitHubTimeoutError):
            client.get_repository("org", "timeout-repo")


def test_401_unauthorized_error() -> None:
    """Test 401 status code raises GitHubAuthenticationError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubAuthenticationError) as exc:
            client.get_repository("org", "private-repo")
        assert exc.value.status_code == 401


def test_403_rate_limit_and_forbidden() -> None:
    """Test 403 rate limit detection and standard 403 forbidden."""

    # 403 Rate limit
    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1700000000"},
            json={"message": "API rate limit exceeded"},
        )

    transport_rl = httpx.MockTransport(rate_limit_handler)
    with httpx.Client(transport=transport_rl) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubRateLimitError) as exc:
            client.get_repository("org", "repo")
        assert exc.value.reset_timestamp == 1700000000

    # 403 Forbidden
    def forbidden_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Resource not accessible by integration"})

    transport_forbid = httpx.MockTransport(forbidden_handler)
    with httpx.Client(transport=transport_forbid) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubForbiddenError) as exc:
            client.get_repository("org", "forbidden-repo")
        assert exc.value.status_code == 403


def test_404_not_found() -> None:
    """Test 404 status raises GitHubNotFoundError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubNotFoundError) as exc:
            client.get_repository("org", "non-existent")
        assert exc.value.status_code == 404


def test_422_validation_error() -> None:
    """Test 422 status raises GitHubValidationError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "Validation Failed", "errors": []})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubValidationError) as exc:
            client.get_repository("org", "invalid-repo")
        assert exc.value.status_code == 422


def test_429_rate_limit() -> None:
    """Test 429 status raises GitHubRateLimitError with retry-after header."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, headers={"retry-after": "60"}, json={"message": "Too Many Requests"}
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubRateLimitError) as exc:
            client.get_repository("org", "repo")
        assert exc.value.retry_after == 60


def test_malformed_response_and_non_json() -> None:
    """Test handling of non-JSON / plain text error responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request Plain Text")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)
        with pytest.raises(GitHubAPIError) as exc:
            client.get_repository("org", "repo")
        assert "Bad Request Plain Text" in str(exc.value)


def test_all_api_methods() -> None:
    """Test all domain API query methods on GitHubClient."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/pulls"):
            return httpx.Response(200, json=[{"id": 1, "title": "PR 1"}])
        elif path.endswith("/issues"):
            return httpx.Response(200, json=[{"id": 2, "title": "Issue 1"}])
        elif "/reviews" in path:
            return httpx.Response(200, json=[{"id": 3, "state": "APPROVED"}])
        elif path.endswith("/comments"):
            return httpx.Response(200, json=[{"id": 4, "body": "Great comment"}])
        elif path.endswith("/commits"):
            return httpx.Response(200, json=[{"sha": "abc1234", "message": "feat: init"}])
        elif path.endswith("/stats/commit_activity"):
            return httpx.Response(
                200, json=[{"total": 10, "week": 1600000000, "days": [0, 1, 2, 3, 4, 0, 0]}]
            )
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as http_client:
        client = GitHubClient(client=http_client)

        prs = client.get_pull_requests("org", "repo")
        assert prs[0]["title"] == "PR 1"

        issues = client.get_issues("org", "repo")
        assert issues[0]["title"] == "Issue 1"

        reviews = client.get_reviews("org", "repo", pull_number=1)
        assert reviews[0]["state"] == "APPROVED"

        comments_repo = client.get_comments("org", "repo")
        assert comments_repo[0]["body"] == "Great comment"

        comments_issue = client.get_comments("org", "repo", issue_number=5)
        assert comments_issue[0]["body"] == "Great comment"

        commits = client.get_commits("org", "repo")
        assert commits[0]["sha"] == "abc1234"

        contrib_commits = client.get_contributor_commits("org", "repo", author="dev1")
        assert contrib_commits[0]["sha"] == "abc1234"

        activity = client.get_commit_activity("org", "repo")
        assert activity[0]["total"] == 10


def test_dependency_and_context_manager() -> None:
    """Test get_github_client dependency provider and context manager."""
    settings = Settings(GITHUB_TOKEN="test_dep_token_999")
    dep_client = get_github_client(settings=settings)
    assert dep_client.token == "test_dep_token_999"

    with GitHubClient() as cm_client:
        assert cm_client is not None
