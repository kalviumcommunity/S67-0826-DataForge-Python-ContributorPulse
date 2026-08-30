# ContributorPulse Ingestion Service & PostgreSQL Persistence

The ContributorPulse ingestion pipeline coordinates GitHub REST API extraction and idempotent persistence of GitHub repositories, contributors, pull requests, issues, reviews, comments, and commits.

---

## API Endpoints

### 1. Trigger Repository Analysis
- **Method / Path:** `POST /api/v1/analyses`
- **Request Body:**
  ```json
  {
    "owner": "kalviumcommunity",
    "repo": "S67-0826-DataForge-Python-ContributorPulse",
    "max_pages": 5
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "status": "success",
    "data": {
      "run_id": "a9b8c7d6-e5f4-4321-abcd-1234567890ab",
      "repository_id": 1,
      "repository_name": "kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse",
      "status": "completed",
      "initiated_at": "2026-08-30T14:20:00Z",
      "completed_at": "2026-08-30T14:20:04Z",
      "duration_seconds": 4.12,
      "total_prs_ingested": 10,
      "total_commits_ingested": 45,
      "total_issues_ingested": 12,
      "total_contributors_ingested": 6,
      "errors_count": 0,
      "error_message": null
    },
    "message": "Repository analysis completed."
  }
  ```

### 2. Get Analysis Run Status
- **Method / Path:** `GET /api/v1/analyses/{analysis_id}`
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "data": {
      "run_id": "a9b8c7d6-e5f4-4321-abcd-1234567890ab",
      "repository_id": 1,
      "repository_name": "kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse",
      "status": "completed",
      "initiated_at": "2026-08-30T14:20:00Z",
      "completed_at": "2026-08-30T14:20:04Z",
      "duration_seconds": 4.12,
      "total_prs_ingested": 10,
      "total_commits_ingested": 45,
      "total_issues_ingested": 12,
      "total_contributors_ingested": 6,
      "errors_count": 0,
      "error_message": null
    },
    "message": "Analysis run completed."
  }
  ```

### 3. Get Repository Details & Counts
- **Method / Path:** `GET /api/v1/repositories/{owner}/{repo}`
- **Response (200 OK):**
  ```json
  {
    "status": "success",
    "data": {
      "id": 1,
      "github_id": 88888,
      "owner": "kalviumcommunity",
      "name": "S67-0826-DataForge-Python-ContributorPulse",
      "full_name": "kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse",
      "description": "ContributorPulse Maintainer Intelligence",
      "primary_language": "Python",
      "stars_count": 120,
      "forks_count": 30,
      "open_issues_count": 5,
      "default_branch": "main",
      "is_private": false,
      "is_fork": false,
      "pushed_at": "2026-08-30T12:00:00Z",
      "created_at": "2026-08-20T10:00:00Z",
      "updated_at": "2026-08-30T14:20:04Z",
      "total_contributors": 6,
      "total_prs": 10,
      "total_issues": 12,
      "total_commits": 45,
      "latest_analysis_run": {
        "run_id": "a9b8c7d6-e5f4-4321-abcd-1234567890ab",
        "repository_id": 1,
        "repository_name": "kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse",
        "status": "completed",
        "initiated_at": "2026-08-30T14:20:00Z",
        "completed_at": "2026-08-30T14:20:04Z",
        "duration_seconds": 4.12,
        "total_prs_ingested": 10,
        "total_commits_ingested": 45,
        "total_issues_ingested": 12,
        "total_contributors_ingested": 6,
        "errors_count": 0,
        "error_message": null
      }
    },
    "message": "Repository details retrieved successfully."
  }
  ```

---

## Idempotence & Error Handling

- **Idempotent Upserts:** Subsequent analysis runs update existing entity records based on unique constraints (`github_id`, `(repository_id, github_id)`, `(repository_id, sha)`) without duplicating records.
- **Non-Fatal Error Logging:** Errors on individual sub-resources (such as reviews or specific comments) are captured into the `ingestion_errors` table and mark the run as `PARTIALLY_COMPLETED`.
- **Fatal Error Handling:** Unhandled catastrophic failures roll back active entity transactions and set `AnalysisRun.status = "FAILED"`.
