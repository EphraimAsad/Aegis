"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import documents, health, projects, providers, search

v1_router = APIRouter()

# Include endpoint routers
v1_router.include_router(health.router, prefix="/health", tags=["health"])
v1_router.include_router(providers.router, prefix="/providers", tags=["providers"])
v1_router.include_router(projects.router, prefix="/projects", tags=["projects"])
v1_router.include_router(search.router, prefix="/search", tags=["search"])
v1_router.include_router(documents.router, prefix="/documents", tags=["documents"])
