# ContributorPulse

## Maintainer Intelligence Platform

ContributorPulse is an open-source maintainer intelligence platform that analyzes GitHub repository activity and measures first-time contributor retention. It ingests repository metadata, contributors, pull requests, issues, reviews, comments, and commits; cleans and stores durable data in PostgreSQL; calculates contributor retention features and repository health KPIs; exposes intelligence via FastAPI; and presents actionable dashboards in Streamlit.

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
│   │   ├── 001_initial_schema.py
│   │   └── 002_add_feature_engine_fields.py
│   └── env.py
├── app.py                      # Streamlit entrypoint
├── api_client.py               # Streamlit-to-FastAPI client bridge
├── github_api.py               # Frontend API helper wrapper
├── pages/                      # Streamlit application pages
│   ├── repository.py           # Repository analysis and overview page
│   ├── contributors.py         # Contributor journeys and tables
│   └── dashboard.py            # Overview dashboard
├── backend/
│   ├── app/
│   │   ├── analytics/          # Retention feature engineering & KPI engine
│   │   ├── api/                # FastAPI routers (health, analyses, repositories, analytics)
│   │   ├── core/               # Configuration and application settings
│   │   ├── db/                 # Database engine, sessions, and connectivity
│   │   ├── integrations/       # External clients (GitHub REST API client)
│   │   ├── models/             # SQLAlchemy ORM domain models
│   │   ├── processing/         # Data cleaning, validation, and normalization pipeline
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── services/           # Ingestion orchestrator and domain services
│   │   └── main.py             # FastAPI application factory and entrypoint
│   ├── tests/                  # Backend test suite (models, migrations, endpoints, client, analytics)
│   ├── requirements.txt        # Backend dependencies
│   └── README.md               # Backend documentation
├── database/                   # Database schemas, models, migrations
├── docs/                       # API contracts, cleaning specs, and metric definitions
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Local PostgreSQL container service
├── .env.example                # Environment configuration template
├── pyproject.toml              # Build and test configuration
├── requirements.txt            # Unified project dependencies
└── README.md
```

---

## Local Development Run Order

To run the complete end-to-end ContributorPulse platform locally:

### 1. Start PostgreSQL Container
```bash
docker compose up -d db
```
Verify health:
```bash
docker compose ps
```

### 2. Apply Database Schema Migrations
```bash
alembic upgrade head
```

### 3. Start the FastAPI Backend Service
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Start the Streamlit Frontend Application
```bash
streamlit run app.py
```
- Web Application: [http://localhost:8501](http://localhost:8501)

### 5. Analyze a Repository
1. Navigate to **🔍 Analyze Repository** via the sidebar.
2. Enter the **Repository Owner** (e.g. `kalviumcommunity`) and **Repository Name** (e.g. `S67-0826-DataForge-Python-ContributorPulse`).
3. Click **🚀 Analyze Repository**.
4. View the real-time analysis status, record counts, verified repository health metrics, and download certified CSV, JSON, and print-ready HTML reports.

---

## Intelligence Exports & Reporting

ContributorPulse exposes certified analytics export endpoints:

- **Contributor Journeys (CSV):** `GET /api/v1/repositories/{owner}/{repo}/exports/contributors.csv`
- **Repository KPIs (CSV):** `GET /api/v1/repositories/{owner}/{repo}/exports/kpis.csv`
- **Intelligence Report (JSON):** `GET /api/v1/repositories/{owner}/{repo}/exports/report.json`
- **Print-Ready Report (HTML):** `GET /api/v1/repositories/{owner}/{repo}/exports/report.html`
- **Production Readiness Probe:** `GET /health/ready`

---

## Continuous Integration & Quality Assurance

The project includes an automated GitHub Actions CI pipeline (`.github/workflows/ci.yml`) that validates:

- **Database Container:** PostgreSQL 15 service with health check (`pg_isready`).
- **Database Migrations:** Full forward execution of Alembic migrations (`alembic upgrade head`).
- **Docker Compose:** Structural syntax validation (`docker compose config`).
- **Code Quality:** Formatting and linting checks (`black`, `isort`, `flake8`).
- **Automated Tests:** Complete backend and frontend test suite with coverage enforcement (`pytest backend/tests -v --cov=backend/app --cov-report=term-missing`).
- **Streamlit Startup:** Full UI component and AppTest simulation validation.

```bash
pytest backend/tests -v --cov=backend/app --cov-report=term-missing
```