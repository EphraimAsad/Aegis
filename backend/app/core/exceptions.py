"""Custom application exceptions."""

from typing import Any


class AegisException(Exception):
    """Base exception for Aegis application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProviderError(AegisException):
    """Exception raised when a provider operation fails."""

    pass


class ProviderNotFoundError(AegisException):
    """Exception raised when a requested provider is not found."""

    pass


class ProviderUnavailableError(AegisException):
    """Exception raised when a provider is unavailable."""

    pass


class DatabaseError(AegisException):
    """Exception raised for database-related errors."""

    pass


class NotFoundError(AegisException):
    """Exception raised when a requested resource is not found."""

    pass


class ValidationError(AegisException):
    """Exception raised for validation errors."""

    pass
