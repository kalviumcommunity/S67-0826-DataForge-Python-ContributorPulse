# ContributorPulse API Contract

## Overview
This document defines the REST API contract for the ContributorPulse FastAPI backend service (`backend/app`).

Base URL: `http://localhost:8000`  
Prefix: `/api/v1`

---

## 1. System & Health Endpoints

### 1.1 Root Endpoint
- **URL:** `GET /`
- **Response (200 OK):**
```json
{
  "message": "Welcome to ContributorPulse Backend API",
  "docs_url": "/docs",
  "health_url": "/health",
  "version": "0.1.0"
}
```

### 1.2 Health Checks
- **URL:** `GET /health` and `GET /api/v1/health`
- **Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "ContributorPulse Backend",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-08-30T13:45:00Z"
}
```

### 1.3 Database Health Check
- **URL:** `GET /health/db` and `GET /api/v1/health/db`
- **Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "ContributorPulse Backend",
  "database": "connected",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-08-30T13:45:00Z"
}
```

---

## 2. Ingestion & Analysis Endpoints

### 2.1 Trigger Repository Analysis
- **URL:** `POST /api/v1/analyses`
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

### 2.2 Get Analysis Status
- **URL:** `GET /api/v1/analyses/{analysis_id}`
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

### 2.3 Get Repository Details
- **URL:** `GET /api/v1/repositories/{owner}/{repo}`
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
  "message": "Repository 'kalviumcommunity/S67-0826-DataForge-Python-ContributorPulse' retrieved successfully."
}
```
