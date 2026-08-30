# ContributorPulse Backend Service

FastAPI-powered intelligence and analytics engine for analyzing GitHub repository health, contributor onboarding journeys, and first-time contributor retention.

---

## Getting Started

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- `pip` or virtualenv package manager

### Environment Configuration
Copy `.env.example` into `.env` at the project root:

```bash
cp .env.example .env
```

Key environment variables:
- `ENVIRONMENT`: `development` | `testing` | `production`
- `API_HOST`: Bind address (default: `0.0.0.0`)
- `API_PORT`: Bind port (default: `8000`)
- `DATABASE_URL`: PostgreSQL connection string (`postgresql://postgres:postgres@localhost:5432/contributor_pulse`)
- `GITHUB_TOKEN`: GitHub personal access token

### Local Database Setup & Migrations

Start the PostgreSQL service using Docker Compose:

```bash
docker compose up -d db
```

Run schema migrations:

```bash
alembic upgrade head
```

To stop the database:
```bash
docker compose stop db
```

To reset the database and volume:
```bash
docker compose down -v
```

---

## Installation & Running Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI application using Uvicorn:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Once running, access:
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
- **Database Health:** [http://localhost:8000/health/db](http://localhost:8000/health/db)

---

## Data Cleaning & Validation Pipeline

The backend features a deterministic data cleaning, validation, and activity linking engine (`backend.app.processing`) that:
- Standardizes all timestamp fields to UTC ISO datetimes
- Sanitizes and normalizes text bodies, titles, and author associations
- Deduplicates entity records based on stable GitHub IDs and unique keys
- Applies dataset-specific missing value imputation strategies
- Quarantines and logs invalid records to the `ingestion_errors` table
- Calculates processing statistics across all stages

---

## Running Tests

Execute the backend test suite with coverage report:

```bash
pytest backend/tests -v --cov=backend/app --cov-report=term-missing
```
