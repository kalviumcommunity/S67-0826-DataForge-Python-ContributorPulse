# PostgreSQL Database Setup and Operations

This document details the PostgreSQL container infrastructure, Docker Compose configuration, lifecycle operations, and CI compatibility for ContributorPulse.

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

### 3. View PostgreSQL Logs
Inspect real-time server logs:

```bash
docker compose logs -f db
```

### 4. Stop Database Container
Stop the running container without losing stored data:

```bash
docker compose stop db
```
Or stop the entire compose stack:

```bash
docker compose down
```

### 5. Reset Database Volume (Wipe Data)
To completely delete the named volume and start with a fresh database:

```bash
docker compose down -v
```

---

## CI & Automated Test Compatibility

In CI environments (e.g. GitHub Actions):
1. Use the official GitHub Actions service container `postgres:16` with healthcheck options.
2. Provide `DATABASE_URL` as an environment variable or test secret.
3. In local or offline unit tests, the backend seamlessly supports in-memory SQLite (`sqlite:///:memory:`) without requiring a live PostgreSQL instance.

---

## Requirements Coverage
- **NFR-10:** Durable PostgreSQL storage with named Docker volumes.
- **NFR-11:** Containerized local development with reproducible health checks.
- **AC-6:** Non-blocking service health and connectivity reporting.
