# ContributorPulse Retention Feature Engineering & KPI Engine

The ContributorPulse analytics layer evaluates cleaned, validated GitHub activity to calculate contributor-level onboarding features and repository-level health KPIs.

---

## PRD Traceability Matrix

- **FR-14 (Contributor Feature Engineering):** Computes first contribution timestamp, first maintainer response time, first review time, merge duration, total PRs, merged PRs, commits, issues, reviews, and comments.
- **FR-15 (Retention Window Logic):** Evaluates 30-day, 60-day, and 90-day return windows based on subsequent contribution timestamps relative to first contribution.
- **FR-16 (Contributor Categorization & Maintainer Flags):** Classifies experience levels (`first_time`, `repeat`, `core`), flags active maintainers, and identifies weekend contribution habits.
- **FR-17 (Explainable Churn Risk Scoring):** Calculates a transparent, rule-based churn risk score (0.0 to 1.0), risk tier (`low`, `medium`, `high`), and human-readable risk reason.
- **FR-18 (Repository-Level KPI Aggregations):** Computes retention rate (30d/90d), merge rate, average review time, average response time, contributor growth rate, and sample size metadata.
- **FR-19 (Composite Health Score Engine):** Computes an explainable, bounded repository health score from 0 to 100.
- **NFR-02 & NFR-05:** Fast, deterministic calculation with idempotent database upserts.
- **AC-2:** Contributor journeys and repository KPIs durably stored in PostgreSQL.

---

## Metric Definitions & Formulas

### 1. Contributor-Level Features

| Metric | Field | Definition & Calculation |
| :--- | :--- | :--- |
| **First Contribution** | `first_contribution_at` | Earliest UTC timestamp among PRs, commits, issues, reviews, and comments authored by the user. |
| **First Response Time** | `first_response_time_seconds` | Seconds from initial PR creation to the earliest comment or review authored by someone other than the PR author. |
| **First Review Time** | `first_pr_review_duration_seconds` | Seconds from initial PR creation to the first code review submitted. |
| **First Merge Duration** | `first_pr_merge_duration_seconds` | Seconds from initial PR creation to `merged_at` (if merged). |
| **30-Day Retention** | `is_retained_30d` | `True` if contributor has an activity timestamp between 1 and 30 days following `first_contribution_at`. |
| **90-Day Retention** | `is_retained_90d` | `True` if contributor has an activity timestamp between 30 and 90 days following `first_contribution_at`. |
| **Experience Level** | `experience_level` | `core` if total contributions >= 10; `repeat` if >= 2; `first_time` otherwise. |
| **Maintainer Flag** | `is_active_maintainer` | `True` if author has submitted reviews, has merged PRs with `MEMBER`/`OWNER`/`COLLABORATOR` association, or administrative role. |
| **Weekend Flag** | `has_weekend_contributions` | `True` if any contribution timestamp occurred on Saturday or Sunday (`weekday >= 5`). |
| **Churn Risk Score** | `churn_risk_score` | Rule-based score (0.0 to 1.0): penalties for slow response (>48h), unmerged initial PR, lack of review, or inactivity (>60d). |
| **Risk Reason** | `risk_reason` | Semicolon-delimited explanation of all risk penalty triggers. |

---

### 2. Repository-Level KPIs

| KPI | Formula / Definition | Sample Handling |
| :--- | :--- | :--- |
| **30-Day Retention Rate** | `(retained_30d_contributors / eligible_30d_contributors) * 100` | Evaluated only for contributors whose first contribution occurred >= 30 days ago. Returns `None` if sample is 0. |
| **90-Day Retention Rate** | `(retained_90d_contributors / eligible_90d_contributors) * 100` | Evaluated only for contributors whose first contribution occurred >= 90 days ago. Returns `None` if sample is 0. |
| **Merge Rate** | `(merged_prs / total_prs) * 100` | Percentage of pull requests successfully merged (0.0 if total PRs is 0). |
| **Avg Review Time** | `mean(first_pr_review_duration_seconds) / 3600` | Average hours to initial PR review across contributors. Returns `None` if no reviews exist. |
| **Avg Response Time** | `mean(first_response_time_seconds) / 3600` | Average hours to initial maintainer comment/review. Returns `None` if no responses exist. |
| **Contributor Growth** | `((new_last_30d - new_prev_30d) / new_prev_30d) * 100` | Percentage change in new first-time contributors in the last 30 days vs preceding 30 days. |
| **Health Score** | Bounded (0 to 100): `MergeComponent (30pts) + ResponseComponent (25pts) + RetentionComponent (25pts) + LowRiskComponent (20pts)` | Fully explainable, strictly bounded between `0.0` and `100.0`. |

---

## Idempotency & Persistence

- Feature values are upserted into the `contributor_features` table using the unique composite key `(repository_id, contributor_id)`.
- Re-running the pipeline updates existing rows without duplicate row creation or data distortion.
