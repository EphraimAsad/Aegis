"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.providers import cleanup_providers, get_provider_manager
from app.sources import cleanup_sources, get_source_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug: {settings.debug}")

    # Initialize providers
    provider_manager = get_provider_manager()
    providers = provider_manager.list_providers()
    print(f"Registered providers: {', '.join(providers)}")

    # Initialize sources
    source_manager = get_source_manager()
    sources = source_manager.list_sources()
    print(f"Registered sources: {', '.join(sources)}")

    yield

    # Shutdown
    print(f"Shutting down {settings.app_name}")
    await cleanup_providers()
    await cleanup_sources()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="Research-focused agentic AI wrapper for academia",
        version=settings.app_version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
