"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, providers

v1_router = APIRouter()

# Include endpoint routers
v1_router.include_router(health.router, prefix="/health", tags=["health"])
v1_router.include_router(providers.router, prefix="/providers", tags=["providers"])
