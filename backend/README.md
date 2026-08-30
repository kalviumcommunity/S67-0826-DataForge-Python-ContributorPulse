# ContributorPulse Backend Service

FastAPI-powered intelligence and analytics engine for analyzing GitHub repository health, contributor onboarding journeys, and first-time contributor retention.

---

## Getting Started

### Prerequisites
- Python 3.10+
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
- `DATABASE_URL`: PostgreSQL connection string
- `GITHUB_TOKEN`: GitHub personal access token

### Installation

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Or install all project dependencies from the root:

```bash
pip install -r requirements.txt
```

---

## Running Locally

Start the FastAPI application using Uvicorn:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or run directly via python:

```bash
python -m backend.app.main
```

Once running, access:
- **Interactive OpenAPI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Running Tests

Execute the backend test suite with coverage report:

```bash
pytest backend/tests -v --cov=backend/app --cov-report=term-missing
```
