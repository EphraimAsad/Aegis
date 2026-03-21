"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.errors import setup_error_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import RequestTrackingMiddleware
from app.providers import cleanup_providers, get_provider_manager
from app.sources import cleanup_sources, get_source_manager

settings = get_settings()

# Setup logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={"environment": settings.environment, "debug": settings.debug},
    )

    # Initialize providers
    provider_manager = get_provider_manager()
    providers = provider_manager.list_providers()
    logger.info(f"Registered providers: {', '.join(providers)}")

    # Initialize sources
    source_manager = get_source_manager()
    sources = source_manager.list_sources()
    logger.info(f"Registered sources: {', '.join(sources)}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
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

    # Request tracking middleware (must be first to wrap all requests)
    app.add_middleware(RequestTrackingMiddleware)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup error handlers
    setup_error_handlers(app)

    # Include API router
    app.include_router(api_router, prefix="/api")

    logger.info("Application configured successfully")

    return app


app = create_app()
