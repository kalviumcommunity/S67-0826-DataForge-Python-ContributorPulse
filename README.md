# ContributorPulse

## Maintainer Intelligence Platform

ContributorPulse is an open-source maintainer intelligence platform that analyzes GitHub repository activity and measures first-time contributor retention. It ingests repository metadata, contributors, pull requests, issues, reviews, comments, and commits; cleans and stores durable data in PostgreSQL; exposes intelligence via FastAPI; and presents actionable dashboards and journeys in Streamlit.

---

## Team Ownership

- **Abilasha (Frontend):** Streamlit pages, charts, filters, KPI cards, UX, and export controls.
- **Keerthana (Backend):** GitHub API client, ingestion, data cleaning, feature engineering, KPI engine, and FastAPI endpoints.
- **Vijay (Database & Infrastructure):** PostgreSQL, SQLAlchemy models, Alembic migrations, SQL views, Docker Compose, GitHub Actions, and documentation.

---

## Architecture Overview

```
ContributorPulse/
├── alembic/                    # Alembic migration environment and versions
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
├── app.py                      # Streamlit entrypoint
├── pages/                      # Streamlit application pages
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI routers (health, ingestion, analytics)
│   │   ├── core/               # Configuration and application settings
│   │   ├── db/                 # Database engine, sessions, and connectivity
│   │   ├── models/             # SQLAlchemy ORM domain models
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── main.py             # FastAPI application factory and entrypoint
│   ├── tests/                  # Backend test suite (models, migrations, endpoints)
│   ├── requirements.txt        # Backend dependencies
│   └── README.md               # Backend documentation
├── database/                   # Database schemas, models, migrations
├── docs/                       # API contracts and architecture specifications
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Local PostgreSQL container service
├── .env.example                # Environment configuration template
├── pyproject.toml              # Build and test configuration
├── requirements.txt            # Unified project dependencies
└── README.md
```

---

## Quickstart & Local Execution

### 1. Environment Setup

Copy `.env.example` to `.env` and fill in your settings:

```bash
cp .env.example .env
```

### 2. Start PostgreSQL Container

```bash
docker compose up -d db
```

Verify health:
```bash
docker compose ps
```

### 3. Run Alembic Database Migrations

```bash
alembic upgrade head
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Start the FastAPI Backend Service

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- Database Check: `http://localhost:8000/health/db`

### 6. Start the Streamlit Frontend

```bash
streamlit run app.py
```

---

## Testing & Quality Assurance

Run the automated test suite with coverage:

```bash
pytest
```