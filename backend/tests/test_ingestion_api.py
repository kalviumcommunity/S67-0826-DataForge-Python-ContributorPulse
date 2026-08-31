"""API tests for repository analysis and ingestion endpoints."""

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import Settings
from backend.app.db.session import get_db
from backend.app.integrations.github import GitHubClient, get_github_client
from backend.app.main import create_app
from backend.app.models.base import Base


@pytest.fixture
def api_test_client():
    """Create a TestClient with shared in-memory database using StaticPool and mock GitHub client."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def mock_github_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if "nonexistent" in path:
            return httpx.Response(404, json={"message": "Not Found"})
        elif "auth-fail" in path:
            return httpx.Response(401, json={"message": "Bad credentials"})
        elif "forbidden-repo" in path:
            return httpx.Response(403, json={"message": "Access Forbidden"})
        elif "rate-limited" in path:
            return httpx.Response(
                429, headers={"retry-after": "60"}, json={"message": "Rate limit"}
            )
        elif "timeout-repo" in path:
            raise httpx.ConnectTimeout("Network timed out")
        elif "server-err" in path:
            return httpx.Response(500, json={"message": "Internal error"})

        if path == "/repos/kalvium/pulse-demo":
            return httpx.Response(
                200,
                json={
                    "id": 88888,
                    "name": "pulse-demo",
                    "full_name": "kalvium/pulse-demo",
                    "owner": {"login": "kalvium", "id": 11111},
                    "description": "Demo repository for ContributorPulse",
                    "stargazers_count": 120,
                    "forks_count": 30,
                    "open_issues_count": 5,
                    "language": "Python",
                    "default_branch": "main",
                    "private": False,
                    "fork": False,
                    "pushed_at": "2026-08-28T14:00:00Z",
                },
            )
        elif path.endswith("/contributors"):
            return httpx.Response(
                200,
                json=[
                    {"id": 11111, "login": "kalvium", "type": "User"},
                    {"id": 22222, "login": "dev_user", "type": "User"},
                ],
            )
        elif path.endswith("/pulls"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 901,
                        "number": 1,
                        "title": "Initial onboarding",
                        "body": "First PR",
                        "state": "closed",
                        "draft": False,
                        "merged": True,
                        "merged_at": "2026-08-20T10:00:00Z",
                        "created_at": "2026-08-19T08:00:00Z",
                        "closed_at": "2026-08-20T10:00:00Z",
                        "author_association": "FIRST_TIME_CONTRIBUTOR",
                        "user": {"id": 22222, "login": "dev_user", "type": "User"},
                    }
                ],
            )
        elif "/reviews" in path:
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 902,
                        "state": "APPROVED",
                        "body": "LGTM",
                        "submitted_at": "2026-08-19T12:00:00Z",
                        "user": {"id": 11111, "login": "kalvium"},
                    }
                ],
            )
        elif path.endswith("/issues"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 903,
                        "number": 2,
                        "title": "First issue",
                        "state": "open",
                        "created_at": "2026-08-21T09:00:00Z",
                        "user": {"id": 22222, "login": "dev_user"},
                    }
                ],
            )
        elif path.endswith("/comments"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": 904,
                        "body": "Issue comment",
                        "created_at": "2026-08-21T10:00:00Z",
                        "issue_url": "https://api.github.com/repos/kalvium/pulse-demo/issues/2",
                        "user": {"id": 11111, "login": "kalvium"},
                    }
                ],
            )
        elif path.endswith("/commits"):
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "c0ffee123456",
                        "commit": {
                            "message": "feat: init",
                            "author": {"name": "dev_user", "date": "2026-08-19T07:00:00Z"},
                            "committer": {"name": "dev_user", "date": "2026-08-19T07:00:00Z"},
                        },
                        "author": {"id": 22222, "login": "dev_user"},
                    }
                ],
            )
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_github_handler)
    mock_http_client = httpx.Client(transport=transport)
    mock_github = GitHubClient(client=mock_http_client, max_retries=0)

    app = create_app(Settings(ENVIRONMENT="testing", DATABASE_URL="sqlite:///:memory:"))
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_github_client] = lambda: mock_github

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)


def test_trigger_analysis_success(api_test_client: TestClient) -> None:
    """Test POST /api/v1/analyses triggers ingestion and returns analysis summary."""
    response = api_test_client.post(
        "/api/v1/analyses",
        json={"owner": "kalvium", "repo": "pulse-demo", "max_pages": 2},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["repository_name"] == "kalvium/pulse-demo"
    assert data["data"]["status"] == "completed"
    assert data["data"]["total_prs_ingested"] == 1
    assert data["data"]["total_issues_ingested"] == 1
    assert data["data"]["total_commits_ingested"] == 1
    assert data["data"]["run_id"] is not None


def test_trigger_analysis_validation_error(api_test_client: TestClient) -> None:
    """Test POST /api/v1/analyses with invalid owner/repo rejects with 422 error."""
    response = api_test_client.post(
        "/api/v1/analyses",
        json={"owner": "kalvium community with spaces!", "repo": "pulse demo"},
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "VALIDATION_ERROR"


def test_trigger_analysis_not_found(api_test_client: TestClient) -> None:
    """Test POST /api/v1/analyses with non-existent repo returns 404."""
    response = api_test_client.post(
        "/api/v1/analyses",
        json={"owner": "nonexistent", "repo": "pulse-demo"},
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_trigger_analysis_error_mappings(api_test_client: TestClient) -> None:
    """Test error mappings for 401, 403, 429, 504, 500."""
    # 401
    res_401 = api_test_client.post("/api/v1/analyses", json={"owner": "auth-fail", "repo": "repo"})
    assert res_401.status_code == 401
    assert res_401.json()["error_code"] == "UNAUTHORIZED"

    # 403
    res_403 = api_test_client.post(
        "/api/v1/analyses", json={"owner": "forbidden-repo", "repo": "repo"}
    )
    assert res_403.status_code == 403
    assert res_403.json()["error_code"] == "FORBIDDEN"

    # 429
    res_429 = api_test_client.post(
        "/api/v1/analyses", json={"owner": "rate-limited", "repo": "repo"}
    )
    assert res_429.status_code == 429
    assert res_429.json()["error_code"] == "RATE_LIMIT_EXCEEDED"

    # 504
    res_504 = api_test_client.post(
        "/api/v1/analyses", json={"owner": "timeout-repo", "repo": "repo"}
    )
    assert res_504.status_code == 504
    assert res_504.json()["error_code"] == "GATEWAY_TIMEOUT"

    # 500
    res_500 = api_test_client.post("/api/v1/analyses", json={"owner": "server-err", "repo": "repo"})
    assert res_500.status_code == 500
    assert res_500.json()["error_code"] == "INTERNAL_SERVER_ERROR"


def test_get_analysis_status_by_id(api_test_client: TestClient) -> None:
    """Test GET /api/v1/analyses/{analysis_id} returns status."""
    post_res = api_test_client.post(
        "/api/v1/analyses",
        json={"owner": "kalvium", "repo": "pulse-demo"},
    )
    run_id = post_res.json()["data"]["run_id"]

    get_res = api_test_client.get(f"/api/v1/analyses/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["run_id"] == run_id
    assert get_res.json()["data"]["status"] == "completed"


def test_get_analysis_not_found(api_test_client: TestClient) -> None:
    """Test GET /api/v1/analyses/{analysis_id} with unknown ID returns 404."""
    response = api_test_client.get("/api/v1/analyses/unknown-run-id-12345")
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_get_repository_details(api_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo} returns details and aggregated counts."""
    api_test_client.post(
        "/api/v1/analyses",
        json={"owner": "kalvium", "repo": "pulse-demo"},
    )

    response = api_test_client.get("/api/v1/repositories/kalvium/pulse-demo")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["full_name"] == "kalvium/pulse-demo"
    assert data["stars_count"] == 120
    assert data["total_prs"] == 1
    assert data["total_issues"] == 1
    assert data["total_commits"] == 1
    assert data["latest_analysis_run"] is not None
    assert data["latest_analysis_run"]["status"] == "completed"


def test_get_repository_not_found(api_test_client: TestClient) -> None:
    """Test GET /api/v1/repositories/{owner}/{repo} returns 404 if not ingested."""
    response = api_test_client.get("/api/v1/repositories/unknown/un-ingested-repo")
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_endpoints_when_db_unavailable() -> None:
    """Test endpoints return 503 SERVICE_UNAVAILABLE when db is None."""
    app = create_app(Settings(ENVIRONMENT="testing", DATABASE_URL="sqlite:///:memory:"))
    app.dependency_overrides[get_db] = lambda: None

    with TestClient(app) as client:
        res_post = client.post("/api/v1/analyses", json={"owner": "org", "repo": "repo"})
        assert res_post.status_code == 503
        assert res_post.json()["error_code"] == "SERVICE_UNAVAILABLE"

        res_get_an = client.get("/api/v1/analyses/123")
        assert res_get_an.status_code == 503

        res_get_repo = client.get("/api/v1/repositories/org/repo")
        assert res_get_repo.status_code == 503
