"""Health check schemas."""

from enum import Enum

from pydantic import BaseModel


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: HealthStatus
    version: str
    environment: str
    database: HealthStatus
    redis: HealthStatus
