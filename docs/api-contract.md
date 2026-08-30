# ContributorPulse API Specification & Contract

The ContributorPulse backend API provides maintainer intelligence, repository health analytics, contributor onboarding metrics, first-time contributor retention insights, and export capabilities.

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
- **FR-26:** Contributor-level CSV export.
- **FR-27:** KPI summary CSV export.
- **FR-28:** Structured JSON intelligence report export.
- **FR-29:** Print-friendly HTML summary report.
- **FR-30:** Production readiness probe (`/health/ready`).
- **NFR-02, NFR-04, NFR-05:** Security boundaries, no credential leakage, deterministic outputs.
- **AC-4:** Production-ready export and CI hardening.

---

## Endpoint Catalog

### 1. Health & Readiness

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Service liveness check (also at `/api/v1/health`). |
| `GET` | `/health/db` | Database connectivity check. |
| `GET` | `/health/ready` | Readiness probe confirming API service and database connectivity. |

---

### 2. Ingestion & Analysis

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/analyses` | Trigger repository ingestion and pipeline execution. |
| `GET` | `/api/v1/analyses/{analysis_id}` | Retrieve analysis execution status and record counts. |
| `GET` | `/api/v1/repositories/{owner}/{repo}` | Fetch persisted repository metadata. |

---

### 3. Analytics & Intelligence

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/repositories/{owner}/{repo}/summary` | Overview metrics and bounded health score (0-100). |
| `GET` | `/api/v1/repositories/{owner}/{repo}/kpis` | Complete KPI metrics with values, units, descriptions, sample sizes. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/contributors` | Paginated contributor journeys with search and multi-field filters. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/funnel` | Contributor onboarding and retention funnel stages. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/response-distribution` | Maintainer response time brackets. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/review-timeline` | Review velocity and duration monthly trends. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/merge-stats` | PR merge statistics and outcome distribution. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/correlations` | Feature vectors ready for correlation analysis. |
| `GET` | `/api/v1/repositories/{owner}/{repo}/high-risk-contributors` | High churn risk contributors and explanatory penalty reasons. |
| `GET` | `/api/v1/repositories/compare` | Side-by-side comparative benchmarking across repositories. |

---

### 4. Exports & Reports

| Method | Path | Description | Content-Type |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/repositories/{owner}/{repo}/exports/contributors.csv` | Downloadable UTF-8 CSV containing all contributor retention metrics and risk scores. | `text/csv; charset=utf-8` |
| `GET` | `/api/v1/repositories/{owner}/{repo}/exports/kpis.csv` | Downloadable UTF-8 CSV containing repository KPIs, units, and sample sizes. | `text/csv; charset=utf-8` |
| `GET` | `/api/v1/repositories/{owner}/{repo}/exports/report.json` | Downloadable complete intelligence report as structured JSON. | `application/json; charset=utf-8` |
| `GET` | `/api/v1/repositories/{owner}/{repo}/exports/report.html` | Downloadable print-friendly formatted HTML summary report. | `text/html; charset=utf-8` |

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
