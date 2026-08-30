"""Streamlit AppTest simulation tests confirming end-to-end page rendering and interaction."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
