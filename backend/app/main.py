"""ContributorPulse FastAPI Application Entrypoint."""

import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.analyses import router as analyses_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.exports import router as exports_router
from backend.app.api.health import router as health_router
from backend.app.api.repositories import router as repositories_router
from backend.app.core.config import Settings, get_settings
from backend.app.schemas.common import ErrorResponse, RootResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("contributor_pulse.backend")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Application factory for ContributorPulse backend service.

    Args:
        settings: Optional Settings override (e.g. for testing).

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app_settings = settings or get_settings()

    app = FastAPI(
        title=app_settings.PROJECT_NAME,
        version=app_settings.VERSION,
        description="Maintainer Intelligence and First-Time Contributor Retention Analytics Platform.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------------------------------
    # Global Exception Handlers for Uniform Error Response Format
    # --------------------------------------------------------------------------

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle standard HTTP exceptions with uniform error envelope."""
        error_code = f"HTTP_{exc.status_code}"
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"
        elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "UNAUTHORIZED"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "FORBIDDEN"
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "BAD_REQUEST"
        elif exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            error_code = "VALIDATION_ERROR"
        elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "RATE_LIMIT_EXCEEDED"
        elif exc.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            error_code = "GATEWAY_TIMEOUT"
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            error_code = "SERVICE_UNAVAILABLE"
        elif exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
            error_code = "INTERNAL_SERVER_ERROR"

        error_response = ErrorResponse(
            status="error",
            error_code=error_code,
            message=str(exc.detail),
            details=None,
            timestamp=datetime.now(timezone.utc),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle schema and parameter validation exceptions with detail list."""
        formatted_details = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            formatted_details.append(
                {
                    "field": loc,
                    "message": error.get("msg", "Invalid value"),
                    "type": error.get("type", "value_error"),
                }
            )

        error_response = ErrorResponse(
            status="error",
            error_code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=formatted_details,
            timestamp=datetime.now(timezone.utc),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch-all unhandled exception handler returning 500 error."""
        logger.exception("Unhandled server exception: %s", exc)
        error_response = ErrorResponse(
            status="error",
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred.",
            details=None,
            timestamp=datetime.now(timezone.utc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(mode="json"),
        )

    # --------------------------------------------------------------------------
    # Root & Routers
    # --------------------------------------------------------------------------

    @app.get(
        "/",
        response_model=RootResponse,
        summary="Service Root Endpoint",
        tags=["Root"],
    )
    def root_endpoint() -> RootResponse:
        """Return welcome information and documentation endpoints."""
        return RootResponse(
            message=f"Welcome to {app_settings.PROJECT_NAME} Backend API",
            docs_url="/docs",
            health_url="/health",
            version=app_settings.VERSION,
        )

    # Mount health endpoint at top-level /health and at /api/v1/health
    app.include_router(health_router)
    app.include_router(health_router, prefix=app_settings.API_V1_STR)

    # Mount Domain Routers under /api/v1
    app.include_router(analyses_router, prefix=app_settings.API_V1_STR)
    app.include_router(repositories_router, prefix=app_settings.API_V1_STR)
    app.include_router(analytics_router, prefix=app_settings.API_V1_STR)
    app.include_router(exports_router, prefix=app_settings.API_V1_STR)

    return app


# Instantiate default application
app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
