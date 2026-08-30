"""Common Pydantic models for API responses and errors."""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class HealthResponse(BaseModel):
    """Schema for healthcheck status endpoint."""

    status: str = Field(
        default="healthy",
        description="Service health status",
        json_schema_extra={"example": "healthy"},
    )
    service: str = Field(
        default="ContributorPulse Backend",
        description="Name of the service",
        json_schema_extra={"example": "ContributorPulse Backend"},
    )
    version: str = Field(
        default="0.1.0",
        description="API version",
        json_schema_extra={"example": "0.1.0"},
    )
    environment: str = Field(
        default="development",
        description="Current environment",
        json_schema_extra={"example": "development"},
    )
    database: Optional[str] = Field(
        default=None,
        description="Database connection status (connected, disconnected, not_configured)",
        json_schema_extra={"example": "connected"},
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp",
    )


class DatabaseHealthResponse(BaseModel):
    """Schema for specific database connectivity health check."""

    status: str = Field(
        ...,
        description="Database status: healthy or degraded",
        json_schema_extra={"example": "healthy"},
    )
    database_connected: bool = Field(
        ...,
        description="Whether database connection is active",
        json_schema_extra={"example": True},
    )
    database_url_configured: bool = Field(
        ...,
        description="Whether DATABASE_URL is set",
        json_schema_extra={"example": True},
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp",
    )


class RootResponse(BaseModel):
    """Schema for root API endpoint."""

    message: str = Field(..., description="Welcome message")
    docs_url: str = Field(..., description="Swagger documentation URL")
    health_url: str = Field(..., description="Health check endpoint URL")
    version: str = Field(..., description="API Version")


class ErrorDetail(BaseModel):
    """Detailed error item for validation or operation errors."""

    field: Optional[str] = Field(default=None, description="Field name where error occurred")
    message: str = Field(..., description="Error message description")
    code: Optional[str] = Field(default=None, description="Specific error code")


class ErrorResponse(BaseModel):
    """Standardized API Error Response schema."""

    status: str = Field(default="error", description="Error status indicator")
    error_code: str = Field(
        ...,
        description="Machine-readable error code",
        json_schema_extra={"example": "NOT_FOUND"},
    )
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional list of error details or validation violations",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error",
    )


class APIResponse(BaseModel, Generic[DataT]):
    """Standardized generic success envelope."""

    status: str = Field(default="success", description="Status string")
    data: DataT = Field(..., description="Response payload")
    message: Optional[str] = Field(default=None, description="Optional informational message")
