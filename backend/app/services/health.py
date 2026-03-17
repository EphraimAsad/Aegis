"""Health check service functions."""

import redis.asyncio as redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import async_engine
from app.schemas.health import HealthStatus

settings = get_settings()


async def check_database_health() -> HealthStatus:
    """Check database connectivity."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return HealthStatus.HEALTHY
    except Exception:
        return HealthStatus.UNHEALTHY


async def check_redis_health() -> HealthStatus:
    """Check Redis connectivity."""
    try:
        client = redis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        return HealthStatus.HEALTHY
    except Exception:
        return HealthStatus.UNHEALTHY
