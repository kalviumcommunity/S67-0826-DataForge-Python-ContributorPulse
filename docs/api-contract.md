# ContributorPulse API Specification & Contract

The ContributorPulse backend API provides maintainer intelligence, repository health analytics, contributor onboarding metrics, and first-time contributor retention insights.

---

## Base URL & Versioning

- **Base URL:** `http://localhost:8000`
- **Version Prefix:** `/api/v1`
- **Interactive Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs) (OpenAPI / Swagger)

---

## PRD Traceability Matrix

- **FR-17:** Explainable churn risk endpoint with scores and penalty reasons.
- **FR-18:** Repository KPI summary and sample size metadata.
- **FR-19:** Repository summary and bounded health score (0-100).
- **FR-20:** Paginated contributor list with multi-parameter filtering.
- **FR-21:** Retention funnel progression data.
- **FR-22:** Response time bracket distribution.
- **FR-23:** Time-series review and response velocity timeline.
- **FR-24:** Pull request merge statistics and duration distribution.
- **FR-25:** Correlation-ready feature vectors and comparative repository analytics.
- **NFR-03 & NFR-05:** Low-latency execution, consistent error envelopes, deterministic results.
- **AC-2:** Complete API surface for Streamlit UI consumption.

---

## Endpoint Catalog

### 1. Health & Status

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness check (also at `/api/v1/health`). |
| `GET` | `/health/db` | Database connectivity check. |

---

### 2. Ingestion & Analysis

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/analyses` | Trigger repository ingestion and pipeline execution. |
| `GET` | `/api/v1/analyses/{analysis_id}` | Retrieve analysis execution status and record counts. |
| `GET` | `/api/v1/repositories/{owner}/{repo}` | Fetch persisted repository metadata. |

---

### 3. Analytics & Intelligence

#### `GET /api/v1/repositories/{owner}/{repo}/summary`
Returns high-level repository stats, retention rates, and composite health score (0 to 100).

```json
{
  "status": "success",
  "data": {
    "repository_id": 1,
    "owner": "kalviumcommunity",
    "name": "S67-0826-DataForge-Python-ContributorPulse",
    "full_name": "kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse",
    "health_score": 85.5,
    "total_contributors": 42,
    "total_prs": 120,
    "total_commits": 310,
    "total_issues": 15,
    "retention_rate_30d": 38.5,
    "retention_rate_90d": 24.1,
    "merge_rate": 78.3,
    "calculated_at": "2026-08-30T15:00:00Z"
  }
}
```

---

#### `GET /api/v1/repositories/{owner}/{repo}/kpis`
Returns complete repository KPIs with units, descriptions, and sample size provenance.

```json
{
  "status": "success",
  "data": {
    "repository_id": 1,
    "owner": "kalviumcommunity",
    "name": "S67-0826-DataForge-Python-ContributorPulse",
    "health_score": 85.5,
    "kpis": {
      "retention_rate_30d": {
        "name": "30-Day Retention Rate",
        "value": 38.5,
        "unit": "%",
        "sample_size": 26,
        "description": "Percentage of first-time contributors who made a repeat contribution within 30 days."
      },
      "merge_rate": {
        "name": "Pull Request Merge Rate",
        "value": 78.3,
        "unit": "%",
        "sample_size": 120,
        "description": "Percentage of total pull requests that were successfully merged."
      }
    },
    "calculated_at": "2026-08-30T15:00:00Z"
  }
}
```

---

#### `GET /api/v1/repositories/{owner}/{repo}/contributors`
Paginated contributor journeys with search and filtering.

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Page size (default: 20, max: 100)
- `experience_level`: `first_time` | `repeat` | `core`
- `retention_status`: `onboarding` | `retained` | `churned`
- `churn_risk_level`: `low` | `medium` | `high`
- `is_active_maintainer`: `true` | `false`
- `search`: Filter by contributor login or name

---

#### `GET /api/v1/repositories/{owner}/{repo}/funnel`
Returns onboarding and retention funnel stages (`Initial Contribution` -> `First PR Merged` -> `Retained 30d` -> `Retained 60d` -> `Retained 90d`).

---

#### `GET /api/v1/repositories/{owner}/{repo}/response-distribution`
Returns response time distribution across standard duration brackets (`< 12h`, `12 - 24h`, `24 - 48h`, `48 - 72h`, `> 72h`, `No Response`).

---

#### `GET /api/v1/repositories/{owner}/{repo}/review-timeline`
Returns historical monthly trends of review duration and maintainer response velocity.

---

#### `GET /api/v1/repositories/{owner}/{repo}/merge-stats`
Returns PR merge rate, outcome counts (merged, closed unmerged, open), and average merge duration.

---

#### `GET /api/v1/repositories/{owner}/{repo}/correlations`
Returns correlation-ready tabular feature data for scatter and trend analysis.

---

#### `GET /api/v1/repositories/{owner}/{repo}/high-risk-contributors`
Returns contributors flagged with high churn risk (`churn_risk_score >= 0.60`) and specific penalty reasons.

---

#### `GET /api/v1/repositories/compare?repos=owner1/repo1,owner2/repo2`
Compares KPIs, health scores, and retention rates across multiple repositories.

---

## Standard Error Envelopes

All errors return consistent, machine-readable JSON envelopes:

```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Repository 'owner/unknown' not found.",
  "details": null,
  "timestamp": "2026-08-30T15:00:00Z"
}
```
