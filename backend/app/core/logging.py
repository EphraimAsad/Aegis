"""Structured logging configuration for Aegis."""

import logging
import sys
from datetime import datetime
from typing import Any

from app.config import get_settings

settings = get_settings()


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs JSON-like structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured output."""
        timestamp = datetime.utcnow().isoformat() + "Z"
        level = record.levelname
        logger_name = record.name
        message = record.getMessage()

        # Base log entry
        log_entry = f"{timestamp} [{level}] {logger_name}: {message}"

        # Add extra fields if present
        extras = []
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            ):
                extras.append(f"{key}={value}")

        if extras:
            log_entry += f" | {' '.join(extras)}"

        # Add exception info if present
        if record.exc_info:
            log_entry += f"\n{self.formatException(record.exc_info)}"

        return log_entry


class DevelopmentFormatter(logging.Formatter):
    """Colorized formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format with colors for terminal output."""
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        level = record.levelname[0]  # First letter only
        message = record.getMessage()

        log_entry = f"{color}{timestamp} {level}{self.RESET} {record.name}: {message}"

        if record.exc_info:
            log_entry += f"\n{self.formatException(record.exc_info)}"

        return log_entry


def setup_logging() -> None:
    """Configure application logging."""
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    # Use different formatter based on environment
    formatter: logging.Formatter
    if settings.environment == "development":
        formatter = DevelopmentFormatter()
    else:
        formatter = StructuredFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing document", extra={"doc_id": 123})
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding extra fields to log messages."""

    def __init__(self, logger: logging.Logger, **extras: Any):
        self.logger = logger
        self.extras = extras

    def __enter__(self) -> "LogContext":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def debug(self, msg: str, **kwargs: Any) -> None:
        self.logger.debug(msg, extra={**self.extras, **kwargs})

    def info(self, msg: str, **kwargs: Any) -> None:
        self.logger.info(msg, extra={**self.extras, **kwargs})

    def warning(self, msg: str, **kwargs: Any) -> None:
        self.logger.warning(msg, extra={**self.extras, **kwargs})

    def error(self, msg: str, **kwargs: Any) -> None:
        self.logger.error(msg, extra={**self.extras, **kwargs})

    def exception(self, msg: str, **kwargs: Any) -> None:
        self.logger.exception(msg, extra={**self.extras, **kwargs})
