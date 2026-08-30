"""Health check and status API routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.app.core.config import Settings, get_settings
from backend.app.schemas.common import HealthResponse

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
    return HealthResponse(
        status="healthy",
        service="ContributorPulse Backend",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )
