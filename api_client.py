"""Streamlit-to-FastAPI backend client for ContributorPulse."""

import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("contributor_pulse.frontend_client")

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT_SECONDS = 10.0


class APIClientError(Exception):
    """Base exception for frontend API client operations."""

    def __init__(
        self, message: str, status_code: Optional[int] = None, details: Optional[Any] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details


class APIConnectionError(APIClientError):
    """Raised when the backend service cannot be reached."""


class APITimeoutError(APIClientError):
    """Raised when an API request times out."""


class APINotFoundError(APIClientError):
    """Raised when a requested resource is not found (404)."""


class APIValidationError(APIClientError):
    """Raised when input parameters fail validation (422)."""


class APIRateLimitError(APIClientError):
    """Raised when the API rate limit is exceeded (429)."""


class APIServerError(APIClientError):
    """Raised when the backend server returns 500 or 503."""


def get_backend_url() -> str:
    """Resolve the FastAPI backend URL from environment variables or Streamlit secrets."""
    url = os.getenv("BACKEND_URL") or os.getenv("API_URL")
    if not url:
        try:
            import streamlit as st

            if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
                url = str(st.secrets["BACKEND_URL"])
        except Exception:
            pass
    return (url or DEFAULT_BACKEND_URL).rstrip("/")


def sanitize_error_message(msg: str) -> str:
    """Sanitize error messages to prevent accidental leakage of tokens or connection strings."""
    if not msg:
        return "An unknown error occurred."
    # Strip tokens (ghp_, github_pat_, etc) and connection strings
    sanitized = re.sub(r"gh[pousr]_[A-Za-z0-9_]{16,}", "[REDACTED_TOKEN]", msg)
    sanitized = re.sub(r"github_pat_[A-Za-z0-9_]{22,}", "[REDACTED_TOKEN]", sanitized)
    sanitized = re.sub(r"postgres(ql)?://[^@]+@[^/]+/[^ \n]+", "[REDACTED_DATABASE_URL]", sanitized)
    return sanitized


def normalize_period(period: Optional[str]) -> Optional[str]:
    """
    Normalize user-facing or programmatic period representations to canonical API strings.

    Supported: '30d', '90d', '180d', '365d', 'all'.
    """
    if not period:
        return None
    p = period.strip().lower()
    if p in ("all", "all ingested history", "all time", "none", "*"):
        return "all"
    if p in ("30d", "last 30 days", "30 days", "30"):
        return "30d"
    if p in ("90d", "last 90 days", "90 days", "90"):
        return "90d"
    if p in ("180d", "last 180 days", "180 days", "180"):
        return "180d"
    if p in ("365d", "last 365 days", "365 days", "365", "1y", "1 year"):
        return "365d"
    return p


class BackendAPIClient:
    """Client for consuming ContributorPulse FastAPI backend endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = (base_url or get_backend_url()).rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request with robust error handling and timeout safety."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        req_timeout = timeout or self.timeout
        try:
            with httpx.Client(timeout=req_timeout) as client:
                response = client.request(method, url, params=params, json=json)
        except httpx.TimeoutException as exc:
            logger.warning("Request timeout calling %s: %s", url, exc)
            raise APITimeoutError(
                "The backend service timed out while processing your request. Please try again later."
            ) from exc
        except httpx.NetworkError as exc:
            logger.warning("Network error calling %s: %s", url, exc)
            raise APIConnectionError(
                f"Cannot connect: Could not connect to the backend at {self.base_url}. Please ensure the server is running."
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during API request: %s", exc)
            raise APIClientError(sanitize_error_message(str(exc))) from exc

        if response.status_code == 404:
            detail = self._extract_error_detail(response, f"Resource not found at {path}")
            raise APINotFoundError(detail, status_code=404)
        elif response.status_code == 422:
            detail = self._extract_error_detail(response, "Request validation failed.")
            raise APIValidationError(detail, status_code=422)
        elif response.status_code == 429:
            detail = self._extract_error_detail(
                response, "Rate limit exceeded. Please try again later."
            )
            raise APIRateLimitError(detail, status_code=429)
        elif response.status_code >= 500:
            detail = self._extract_error_detail(response, "Backend internal server error.")
            raise APIServerError(detail, status_code=response.status_code)
        elif response.status_code >= 400:
            detail = self._extract_error_detail(
                response, f"Request failed with status {response.status_code}"
            )
            raise APIClientError(detail, status_code=response.status_code)

        try:
            return response.json()
        except Exception as exc:
            raise APIClientError("Invalid or malformed JSON received from backend.") from exc

    def _extract_error_detail(self, response: httpx.Response, fallback: str) -> str:
        """Extract clean human-readable error messages from error envelope."""
        try:
            body = response.json()
            if isinstance(body, dict):
                msg = body.get("message") or body.get("detail")
                if msg:
                    return sanitize_error_message(str(msg))
        except Exception:
            pass
        return fallback

    # --------------------------------------------------------------------------
    # Health & Connectivity
    # --------------------------------------------------------------------------

    def check_health(self) -> Dict[str, Any]:
        """Check backend service liveness."""
        return self._request("GET", "/health")

    def check_db_health(self) -> Dict[str, Any]:
        """Check database connectivity health."""
        return self._request("GET", "/health/db")

    # --------------------------------------------------------------------------
    # Ingestion & Analyses
    # --------------------------------------------------------------------------

    def trigger_analysis(
        self,
        owner: str,
        repo: str,
        max_pages: Optional[int] = 2,
    ) -> Dict[str, Any]:
        """Trigger repository ingestion and analysis run with extended timeout."""
        payload = {"owner": owner.strip(), "repo": repo.strip()}
        if max_pages:
            payload["max_pages"] = max_pages
        res = self._request("POST", "/api/v1/analyses", json=payload, timeout=120.0)
        return res.get("data", res)

    def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve execution status and record counts for an analysis run."""
        res = self._request("GET", f"/api/v1/analyses/{analysis_id}")
        return res.get("data", res)

    def get_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fetch persisted repository metadata."""
        try:
            res = self._request("GET", f"/api/v1/repositories/{owner}/{repo}")
            return res.get("data", res)
        except APINotFoundError:
            return None

    # --------------------------------------------------------------------------
    # Analytics & KPIs with Time-Period Support
    # --------------------------------------------------------------------------

    def get_repository_summary(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch repository overview metrics and health score filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/summary", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_repository_kpis(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch complete repository KPIs with sample sizes and units filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request("GET", f"/api/v1/repositories/{owner}/{repo}/kpis", params=params)
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_contributors(
        self,
        owner: str,
        repo: str,
        page: int = 1,
        per_page: int = 20,
        experience_level: Optional[str] = None,
        retention_status: Optional[str] = None,
        churn_risk_level: Optional[str] = None,
        is_active_maintainer: Optional[bool] = None,
        search: Optional[str] = None,
        period: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch paginated contributor journey records filtered by period."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if experience_level:
            params["experience_level"] = experience_level
        if retention_status:
            params["retention_status"] = retention_status
        if churn_risk_level:
            params["churn_risk_level"] = churn_risk_level
        if is_active_maintainer is not None:
            params["is_active_maintainer"] = is_active_maintainer
        if search:
            params["search"] = search
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period

        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/contributors", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_retention_funnel(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch retention funnel progression data filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request("GET", f"/api/v1/repositories/{owner}/{repo}/funnel", params=params)
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_response_distribution(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch response-time bracket distribution filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/response-distribution", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_review_timeline(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch chronological review and response speed timeline filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/review-timeline", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_merge_stats(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch PR merge outcomes and duration stats filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/merge-stats", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_correlation_data(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch correlation-ready feature data filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/correlations", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def get_high_risk_contributors(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch high churn risk contributors filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        try:
            res = self._request(
                "GET", f"/api/v1/repositories/{owner}/{repo}/high-risk-contributors", params=params
            )
            return res.get("data", res)
        except APINotFoundError:
            return None

    def compare_repositories(self, repos: List[str]) -> Optional[Dict[str, Any]]:
        """Fetch side-by-side comparison for multiple repositories."""
        if not repos:
            return None
        try:
            res = self._request(
                "GET", "/api/v1/repositories/compare", params={"repos": ",".join(repos)}
            )
            return res.get("data", res)
        except (APINotFoundError, APIValidationError):
            return None

    # --------------------------------------------------------------------------
    # Exports & Reporting with Time-Period Support
    # --------------------------------------------------------------------------

    def _request_raw(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
        """Execute request and return raw binary/text bytes."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=params)
                if response.status_code == 200:
                    return response.content
                return None
        except Exception:
            return None

    def export_contributors_csv(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[bytes]:
        """Fetch contributor-level CSV export filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        return self._request_raw(
            f"/api/v1/repositories/{owner}/{repo}/exports/contributors.csv", params=params
        )

    def export_kpis_csv(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[bytes]:
        """Fetch KPI and repository summary CSV export filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        return self._request_raw(
            f"/api/v1/repositories/{owner}/{repo}/exports/kpis.csv", params=params
        )

    def export_report_json(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[bytes]:
        """Fetch full intelligence JSON report filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        return self._request_raw(
            f"/api/v1/repositories/{owner}/{repo}/exports/report.json", params=params
        )

    def export_report_html(
        self, owner: str, repo: str, period: Optional[str] = None
    ) -> Optional[bytes]:
        """Fetch printable HTML intelligence report filtered by period."""
        params = {}
        norm_period = normalize_period(period)
        if norm_period:
            params["period"] = norm_period
        return self._request_raw(
            f"/api/v1/repositories/{owner}/{repo}/exports/report.html", params=params
        )
