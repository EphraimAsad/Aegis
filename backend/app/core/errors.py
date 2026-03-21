"""Error handling for Aegis API."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class AegisError(Exception):
    """Base exception for Aegis application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "AEGIS_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class ProviderError(AegisError):
    """Error from AI provider."""

    def __init__(self, message: str, provider: str, details: dict | None = None):
        super().__init__(
            message=message,
            error_code="PROVIDER_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"provider": provider, **(details or {})},
        )
        self.provider = provider


class SourceError(AegisError):
    """Error from academic source."""

    def __init__(self, message: str, source: str, details: dict | None = None):
        super().__init__(
            message=message,
            error_code="SOURCE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"source": source, **(details or {})},
        )
        self.source = source


class DocumentNotFoundError(AegisError):
    """Document not found."""

    def __init__(self, document_id: int):
        super().__init__(
            message=f"Document {document_id} not found",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"document_id": document_id},
        )


class ProjectNotFoundError(AegisError):
    """Project not found."""

    def __init__(self, project_id: int):
        super().__init__(
            message=f"Project {project_id} not found",
            error_code="PROJECT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"project_id": project_id},
        )


class JobNotFoundError(AegisError):
    """Job not found."""

    def __init__(self, job_id: int):
        super().__init__(
            message=f"Job {job_id} not found",
            error_code="JOB_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"job_id": job_id},
        )


class RateLimitError(AegisError):
    """Rate limit exceeded."""

    def __init__(self, service: str, retry_after: int | None = None):
        details = {"service": service}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=f"Rate limit exceeded for {service}",
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
        )


class ConfigurationError(AegisError):
    """Configuration error."""

    def __init__(self, message: str, config_key: str | None = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"config_key": config_key} if config_key else None,
        )


def setup_error_handlers(app: FastAPI) -> None:
    """Register error handlers with the FastAPI app."""

    @app.exception_handler(AegisError)
    async def aegis_error_handler(request: Request, exc: AegisError) -> JSONResponse:
        """Handle Aegis application errors."""
        request_id = getattr(request.state, "request_id", None)

        logger.error(
            f"{exc.error_code}: {exc.message}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "request_id": request_id,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.error_code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "request_id": request_id,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="HTTP_ERROR",
                message=str(exc.detail),
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        request_id = getattr(request.state, "request_id", None)

        # Extract validation error details
        errors = []
        for error in exc.errors():
            location = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": location,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        logger.warning(
            f"Validation error: {len(errors)} field(s)",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "errors": errors,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": errors},
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unhandled exceptions."""
        request_id = getattr(request.state, "request_id", None)

        logger.exception(
            f"Unhandled exception: {exc}",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="INTERNAL_ERROR",
                message="An unexpected error occurred",
                request_id=request_id,
            ).model_dump(),
        )
