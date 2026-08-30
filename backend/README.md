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

## GitHub REST API Integration

The backend includes a production-grade GitHub client (`backend.app.integrations.github.GitHubClient`) featuring:
- Authorization header handling from environment configuration
- Multi-page pagination
- Rate-limit response handling (`x-ratelimit-remaining`, `retry-after`)
- Transient failure retry with bounded exponential backoff
- Typed exception hierarchy (`GitHubAuthenticationError`, `GitHubRateLimitError`, `GitHubNotFoundError`, `GitHubValidationError`, etc.)

---

## Running Tests

Execute the backend test suite with coverage report:

```bash
pytest backend/tests -v --cov=backend/app --cov-report=term-missing
```
