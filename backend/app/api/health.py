"""Health check and status API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.app.core.config import Settings, get_settings
from backend.app.db.session import check_db_connectivity, get_engine
from backend.app.schemas.common import DatabaseHealthResponse, HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the operational status, version, environment, and UTC timestamp of the backend service. Does not require external credentials.",
)
def get_health_status(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    """
    Check the health of the ContributorPulse API service.

    Args:
        settings: Application settings injected via dependency injection.

    Returns:
        HealthResponse: Service health metadata.
    """
    db_status = "not_configured"
    if settings.DATABASE_URL:
        engine = get_engine(settings.DATABASE_URL)
        db_status = "connected" if check_db_connectivity(engine) else "disconnected"

    return HealthResponse(
        status="healthy",
        service="ContributorPulse Backend",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/health/db",
    response_model=DatabaseHealthResponse,
    summary="Database Connectivity Check",
    description="Returns database connectivity status and configuration presence.",
)
def get_database_health(
    settings: Settings = Depends(get_settings),
) -> DatabaseHealthResponse:
    """
    Check database connectivity.

    Args:
        settings: Application settings.

    Returns:
        DatabaseHealthResponse: Status of database connection.
    """
    is_configured = bool(settings.DATABASE_URL)
    engine = get_engine(settings.DATABASE_URL) if is_configured else None
    is_connected = check_db_connectivity(engine) if is_configured else False
    status_str = "healthy" if is_connected else ("degraded" if is_configured else "unconfigured")

    return DatabaseHealthResponse(
        status=status_str,
        database_connected=is_connected,
        database_url_configured=is_configured,
        timestamp=datetime.now(timezone.utc),
    )
