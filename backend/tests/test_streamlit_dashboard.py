"""Unit and smoke tests for ContributorPulse Streamlit dashboard components and views."""

import pytest
import pandas as pd
from api_client import BackendAPIClient, sanitize_error_message
from pages.dashboard import render_health_badge, safe_metric


def test_render_health_badge() -> None:
    """Test health classification badge logic."""
    assert "Excellent" in render_health_badge(95.0)
    assert "Good" in render_health_badge(75.0)
    assert "Moderate" in render_health_badge(50.0)
    assert "At Risk" in render_health_badge(30.0)


def test_safe_metric_formatting() -> None:
    """Test safe formatting for metrics, empty values, floats, and percentages."""
    assert safe_metric(85.45, "%") == "85.5%"
    assert safe_metric(None, "%", default="N/A") == "N/A"
    assert safe_metric(42, " PRs") == "42 PRs"
    assert safe_metric("100", "") == "100"


def test_funnel_dataframe_structure() -> None:
    """Test retention funnel data converts cleanly into DataFrame."""
    stages = [
        {"stage": "Initial Contribution", "contributor_count": 100, "conversion_rate": 100.0, "drop_off_count": 0},
        {"stage": "First PR Merged", "contributor_count": 75, "conversion_rate": 75.0, "drop_off_count": 25},
        {"stage": "Retained 30d", "contributor_count": 35, "conversion_rate": 35.0, "drop_off_count": 40},
    ]
    df = pd.DataFrame(stages)
    assert len(df) == 3
    assert "conversion_rate" in df.columns
    assert df["contributor_count"].iloc[0] == 100


def test_response_distribution_dataframe() -> None:
    """Test response distribution bracket data conversion."""
    buckets = [
        {"bracket": "< 12h", "count": 15, "percentage": 50.0},
        {"bracket": "12 - 24h", "count": 10, "percentage": 33.3},
        {"bracket": "> 72h", "count": 5, "percentage": 16.7},
    ]
    df = pd.DataFrame(buckets)
    assert len(df) == 3
    assert df["percentage"].sum() == pytest.approx(100.0, abs=0.1)


def test_high_risk_contributor_data_structure() -> None:
    """Test high risk contributor dataframe columns."""
    items = [
        {
            "login": "churn_user_1",
            "churn_risk_score": 0.85,
            "churn_risk_level": "high",
            "experience_level": "first_time",
            "risk_reason": "No response for > 72h; Unmerged PR",
            "first_response_hours": 96.0,
            "first_review_hours": None,
        }
    ]
    df = pd.DataFrame(items)
    assert len(df) == 1
    assert df["churn_risk_score"].iloc[0] >= 0.60
    assert "No response" in df["risk_reason"].iloc[0]


def test_repository_comparison_dataframe() -> None:
    """Test multi-repository comparison structure."""
    repos = [
        {"full_name": "org1/repo1", "health_score": 85.0, "retention_rate_30d": 40.0, "merge_rate": 80.0, "total_contributors": 50, "total_prs": 120},
        {"full_name": "org2/repo2", "health_score": 65.0, "retention_rate_30d": 20.0, "merge_rate": 55.0, "total_contributors": 30, "total_prs": 80},
    ]
    df = pd.DataFrame(repos)
    assert len(df) == 2
    assert df["health_score"].iloc[0] > df["health_score"].iloc[1]


def test_no_credential_leakage_in_error_render() -> None:
    """Ensure error messages rendered never expose raw GitHub tokens or passwords."""
    raw_error = "Failed to connect: postgresql://admin:super_secret@localhost:5432/db with token ghp_secretToken12345678"
    sanitized = sanitize_error_message(raw_error)
    assert "super_secret" not in sanitized
    assert "ghp_secretToken" not in sanitized
    assert "[REDACTED_DATABASE_URL]" in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
