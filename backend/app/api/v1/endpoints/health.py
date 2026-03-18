"""Health check endpoints."""

from fastapi import APIRouter

from app.dependencies import SettingsDep
from app.schemas.health import HealthResponse, HealthStatus
from app.services.health import check_database_health, check_redis_health

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check(settings: SettingsDep) -> HealthResponse:
    """
    Check the health of the application and its dependencies.

    Returns the status of:
    - Application itself
    - Database connection
    - Redis connection
    """
    # Check dependencies
    db_status = await check_database_health()
    redis_status = await check_redis_health()

    # Determine overall status
    all_healthy = (
        db_status == HealthStatus.HEALTHY and redis_status == HealthStatus.HEALTHY
    )
    overall_status = HealthStatus.HEALTHY if all_healthy else HealthStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        database=db_status,
        redis=redis_status,
    )


@router.get("/live")
async def liveness_probe() -> dict[str, str]:
    """
    Kubernetes liveness probe endpoint.

    Returns OK if the application is running.
    """
    return {"status": "ok"}


@router.get("/ready")
async def readiness_probe() -> dict[str, str]:
    """
    Kubernetes readiness probe endpoint.

    Returns OK if the application is ready to receive traffic.
    """
    db_status = await check_database_health()
    redis_status = await check_redis_health()

    if db_status == HealthStatus.HEALTHY and redis_status == HealthStatus.HEALTHY:
        return {"status": "ok"}

    return {"status": "not ready"}
