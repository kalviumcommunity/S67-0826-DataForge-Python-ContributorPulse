# PostgreSQL Database Setup, Schema & Migrations

This document details the PostgreSQL container infrastructure, Docker Compose configuration, SQLAlchemy schema, Alembic migration workflows, and CI compatibility for ContributorPulse.

---

## Architecture & Configuration

- **Database Engine:** PostgreSQL 16 Alpine (`postgres:16-alpine`)
- **Container Name:** `contributor_pulse_db`
- **Volume Storage:** Named volume `contributor_pulse_postgres_data` mapping to `/var/lib/postgresql/data`
- **Default Database:** `contributor_pulse`
- **Default Port:** `5432`

### Environment Variables

All database parameters are configurable via environment variables in `.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `POSTGRES_DB` | PostgreSQL database name | `contributor_pulse` |
| `POSTGRES_USER` | PostgreSQL superuser username | `postgres` |
| `POSTGRES_PASSWORD` | PostgreSQL superuser password | `postgres` |
| `POSTGRES_PORT` | Local host port mapped to container 5432 | `5432` |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql://postgres:postgres@localhost:5432/contributor_pulse` |

---

## Local Database Lifecycle Operations

### 1. Start Database Container
Start the PostgreSQL container in background:

```bash
docker compose up -d db
```

### 2. Verify Container Health & Status
Check container status and built-in healthcheck:

```bash
docker compose ps
```

Expected health status: `healthy` (using `pg_isready`).

### 3. Run Database Migrations
Apply the normalized schema via Alembic:

```bash
alembic upgrade head
```

### 4. View PostgreSQL Logs
Inspect real-time server logs:

```bash
docker compose logs -f db
```

### 5. Stop Database Container
Stop the running container without losing stored data:

```bash
docker compose stop db
```
Or stop the entire compose stack:

```bash
docker compose down
```

### 6. Reset Database Volume (Wipe Data)
To completely delete the named volume and start with a fresh database:

```bash
docker compose down -v
```

---

## Alembic Migration Commands

| Command | Action |
| :--- | :--- |
| `alembic upgrade head` | Run all pending migrations to latest revision |
| `alembic downgrade -1` | Revert the latest migration step |
| `alembic downgrade base` | Revert all migrations to an empty database |
| `alembic current` | Display current active revision |
| `alembic history` | Show migration history list |

---

## Requirements Coverage
- **FR-07, FR-09, FR-11, FR-13, FR-14, FR-15, FR-17:** Complete database models for repositories, contributors, pull requests, issues, reviews, comments, commits, feature retention metrics, and ingestion error logs.
- **NFR-10:** Durable PostgreSQL storage with named Docker volumes.
- **NFR-11:** Containerized local development with reproducible health checks.
- **AC-6:** Non-blocking service health and connectivity reporting.
