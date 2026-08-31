"""Typed environment and application configuration."""

import re
from functools import lru_cache
from typing import List, Optional, Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # General project metadata
    PROJECT_NAME: str = Field(default="ContributorPulse", description="Project Name")
    VERSION: str = Field(default="0.1.0", description="API Version")
    API_V1_STR: str = Field(default="/api/v1", description="API prefix for v1 routes")
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment: development, testing, staging, production",
    )
    DEBUG: bool = Field(default=False, description="Debug mode")

    # API Server configuration
    API_HOST: str = Field(default="0.0.0.0", description="Host address to bind the API server")
    API_PORT: int = Field(default=8000, description="Port number to bind the API server")

    # Security and CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["*"],
        description="Allowed CORS origins as a list or comma-separated string",
    )

    # External Integrations
    GITHUB_TOKEN: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token for API ingestion",
    )

    # Database
    DATABASE_URL: Optional[str] = Field(
        default=None,
        description="PostgreSQL Database Connection URL",
    )

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string or list into a list of strings."""
        if isinstance(v, str):
            if not v.strip():
                return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        """
        Validate strict configuration requirements for production environments.

        Ensures that production deployments do not run with missing database configurations.
        """
        env = self.ENVIRONMENT.lower()
        if env == "production":
            if not self.DATABASE_URL or "localhost" in self.DATABASE_URL:
                raise ValueError(
                    "DATABASE_URL must be explicitly configured with a valid remote PostgreSQL URI in production."
                )
        return self

    @property
    def is_production(self) -> bool:
        """Return True if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Return True if running in testing environment."""
        return self.ENVIRONMENT.lower() == "testing"

    def masked_github_token(self) -> Optional[str]:
        """Return a masked representation of the GitHub token for safe logging."""
        if not self.GITHUB_TOKEN:
            return None
        if len(self.GITHUB_TOKEN) <= 8:
            return "****"
        return f"{self.GITHUB_TOKEN[:4]}...{self.GITHUB_TOKEN[-4:]}"

    def masked_database_url(self) -> Optional[str]:
        """Return a masked database URL hiding credentials."""
        if not self.DATABASE_URL:
            return None
        # Mask password in postgresql://user:password@host:port/db
        return re.sub(r":([^:@]+)@", r":****@", self.DATABASE_URL)

    def __repr__(self) -> str:
        """Safe representation hiding credentials."""
        return (
            f"Settings(PROJECT_NAME='{self.PROJECT_NAME}', "
            f"VERSION='{self.VERSION}', "
            f"ENVIRONMENT='{self.ENVIRONMENT}', "
            f"API_HOST='{self.API_HOST}', "
            f"API_PORT={self.API_PORT}, "
            f"GITHUB_TOKEN='{self.masked_github_token()}', "
            f"DATABASE_URL='{self.masked_database_url()}')"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    Returns:
        Settings: Application configuration loaded from environment.
    """
    return Settings()
