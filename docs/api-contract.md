# ContributorPulse API Contract

## Specification Overview

The ContributorPulse backend exposes RESTful HTTP APIs built on FastAPI. This document defines the standard contracts, response envelopes, error handling guidelines, and core service endpoints.

- **Base URL:** `http://<host>:<port>`
- **API Version Prefix:** `/api/v1`
- **Documentation (Swagger):** `/docs`
- **Specification (OpenAPI):** `/openapi.json`

---

## Standards and Guidelines

### 1. Requirements Coverage
- **FR-06:** Standardized error response and health endpoint format across all API interfaces.
- **NFR-04:** Robust configuration management with typed environment loading and zero secrets exposure in logs or payloads.
- **NFR-05:** Stable API response contracts with UTC timestamps and Pydantic validation.
- **AC-6:** Health check endpoint (`GET /health` and `GET /api/v1/health`) must be credential-independent and return operational status.

### 2. Standard Error Response Envelope

All API errors return a standard JSON envelope:

```json
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Resource could not be located.",
  "details": null,
  "timestamp": "2026-08-30T13:30:00.000000Z"
}
```

#### Common Error Codes
| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400` | `BAD_REQUEST` | Malformed request parameters or invalid payload |
| `401` | `UNAUTHORIZED` | Missing or invalid authentication credentials |
| `403` | `FORBIDDEN` | Insufficient permissions for the requested resource |
| `404` | `NOT_FOUND` | Endpoint or entity does not exist |
| `422` | `VALIDATION_ERROR` | Schema validation error with field-level `details` |
| `500` | `INTERNAL_SERVER_ERROR` | Unexpected server fault (sanitized) |

---

## Core Endpoints

### 1. Health Check
Returns the operational health, version, environment, and current UTC time. Does not require external database or GitHub credentials.

- **Path:** `GET /health` and `GET /api/v1/health`
- **Auth:** None
- **Response `200 OK`:**
  ```json
  {
    "status": "healthy",
    "service": "ContributorPulse Backend",
    "version": "0.1.0",
    "environment": "development",
    "timestamp": "2026-08-30T13:30:00.000000Z"
  }
  ```

### 2. Root Welcome Endpoint
Returns service info and quick links to interactive documentation.

- **Path:** `GET /`
- **Auth:** None
- **Response `200 OK`:**
  ```json
  {
    "message": "Welcome to ContributorPulse Backend API",
    "docs_url": "/docs",
    "health_url": "/health",
    "version": "0.1.0"
  }
  ```
