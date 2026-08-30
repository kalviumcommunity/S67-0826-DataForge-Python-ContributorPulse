"""API routers package."""

from backend.app.api.analyses import router as analyses_router
from backend.app.api.health import router as health_router
from backend.app.api.repositories import router as repositories_router

__all__ = [
    "health_router",
    "analyses_router",
    "repositories_router",
]
