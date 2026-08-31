"""Streamlit AppTest simulation tests confirming end-to-end page rendering and interaction."""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def mock_api_for_apptest(monkeypatch: pytest.MonkeyPatch):
    """Mock API responses so AppTest runs deterministically and instantly."""

    def mock_request(self, method, url, **kwargs):
        url_str = str(url)
        if "/summary" in url_str:
            data = {
                "status": "success",
                "data": {
                    "health_score": 85.0,
                    "total_contributors": 12,
                    "retention_rate_30d": 50.0,
                    "merge_rate": 75.0,
                },
            }
        elif "/kpis" in url_str:
            data = {
                "status": "success",
                "data": {
                    "health_score": 85.0,
                    "kpis": {"merge_rate": {"value": 75.0, "unit": "%", "sample_size": 10}},
                },
            }
        elif "/contributors" in url_str:
            data = {
                "status": "success",
                "data": {
                    "items": [
                        {"login": "alice", "churn_risk_score": 0.2, "churn_risk_level": "low"}
                    ],
                    "pagination": {"total_records": 1, "total_pages": 1},
                },
            }
        elif "/funnel" in url_str:
            data = {
                "status": "success",
                "data": {
                    "stages": [
                        {
                            "stage": "Initial Contribution",
                            "contributor_count": 10,
                            "conversion_rate": 100.0,
                            "drop_off_count": 0,
                        }
                    ]
                },
            }
        elif "/response-distribution" in url_str:
            data = {
                "status": "success",
                "data": {"buckets": [{"bracket": "< 12h", "count": 5, "percentage": 50.0}]},
            }
        elif "/review-timeline" in url_str:
            data = {
                "status": "success",
                "data": {
                    "timeline": [
                        {
                            "period": "2026-08",
                            "average_review_hours": 12.0,
                            "average_response_hours": 4.0,
                        }
                    ]
                },
            }
        elif "/merge-stats" in url_str:
            data = {
                "status": "success",
                "data": {
                    "total_prs": 10,
                    "merged_prs": 7,
                    "closed_unmerged_prs": 2,
                    "open_prs": 1,
                    "merge_rate": 70.0,
                },
            }
        elif "/high-risk-contributors" in url_str:
            data = {"status": "success", "data": {"high_risk_count": 0, "items": []}}
        elif "/compare" in url_str:
            data = {
                "status": "success",
                "data": {
                    "repositories": [
                        {
                            "full_name": "test-org/test-repo",
                            "health_score": 85.0,
                            "retention_rate_30d": 50.0,
                            "merge_rate": 75.0,
                        }
                    ]
                },
            }
        else:
            data = {
                "status": "success",
                "data": {
                    "id": 1,
                    "stars_count": 100,
                    "forks_count": 20,
                    "open_issues_count": 5,
                    "full_name": "test-org/test-repo",
                },
            }
        return httpx.Response(200, json=data, request=httpx.Request(method, url))

    def mock_get(self, url, **kwargs):
        return mock_request(self, "GET", url, **kwargs)

    monkeypatch.setattr(httpx.Client, "request", mock_request)
    monkeypatch.setattr(httpx.Client, "get", mock_get)


def test_app_main_page_renders_cleanly() -> None:
    """Test app.py home page renders without exceptions."""
    app_file = str(REPO_ROOT / "app.py")
    at = AppTest.from_file(app_file, default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.title) >= 1
    assert "ContributorPulse" in at.title[0].value


def test_dashboard_empty_state_renders() -> None:
    """Test pages/dashboard.py renders clean empty prompt when no repo is selected."""
    dash_file = str(REPO_ROOT / "pages" / "dashboard.py")
    at = AppTest.from_file(dash_file, default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.info) >= 1
    assert "Enter a GitHub repository" in at.info[0].value


def test_dashboard_with_mocked_repository_session() -> None:
    """Test pages/dashboard.py renders overview when repository is set in session state."""
    dash_file = str(REPO_ROOT / "pages" / "dashboard.py")
    at = AppTest.from_file(dash_file, default_timeout=15)
    at.session_state["owner"] = "test-org"
    at.session_state["repository"] = "test-repo"
    at.session_state["selected_view"] = "🏛️ Overview & Health"
    at.session_state["time_period"] = "Last 30 Days"
    at.run()
    assert not at.exception
    assert len(at.title) >= 1


def test_contributors_page_empty_state() -> None:
    """Test pages/contributors.py renders prompt when repo not set."""
    contrib_file = str(REPO_ROOT / "pages" / "contributors.py")
    at = AppTest.from_file(contrib_file, default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.info) >= 1


def test_repository_page_renders() -> None:
    """Test pages/repository.py renders form inputs and button."""
    repo_file = str(REPO_ROOT / "pages" / "repository.py")
    at = AppTest.from_file(repo_file, default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.text_input) >= 2
    assert len(at.button) >= 1
