"""
Structured Logging Middleware

Provides JSON-formatted request/response logging for observability.
Includes request IDs, timing, and contextual information.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variable for request ID (thread-safe)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Logging filter to add request ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get("")
        return True


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in a format suitable for log aggregation systems
    like ELK Stack, Loki, or CloudWatch.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key in ["user_id", "method", "path", "status_code", "duration_ms", "client_ip"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Features:
    - Unique request ID for tracing
    - Request/response timing
    - Client IP tracking
    - User identification (when authenticated)
    - JSON-formatted output
    """

    def __init__(self, app: ASGIApp, logger_name: str = "cms.access"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        # Start timing
        start_time = time.perf_counter()

        # Get client IP (handle proxies)
        client_ip = request.headers.get(
            "X-Forwarded-For", request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")
        )
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_request(
                request=request,
                status_code=500,
                duration_ms=duration_ms,
                client_ip=client_ip,
                request_id=request_id,
                error=str(e),
            )
            raise

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        # Log the request
        self._log_request(
            request=request,
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=client_ip,
            request_id=request_id,
        )

        return response

    def _log_request(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        client_ip: str,
        request_id: str,
        error: str | None = None,
    ) -> None:
        """Log the request with structured data."""
        # Skip health check endpoints to reduce noise
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return

        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Extract user ID from request state if available
        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)

        # Create log record with extra fields
        extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }

        if user_id:
            extra["user_id"] = user_id

        message = f"{request.method} {request.url.path} - {status_code} ({duration_ms:.2f}ms)"
        if error:
            message += f" - Error: {error}"

        self.logger.log(log_level, message, extra=extra)


def setup_structured_logging(
    log_level: str = "INFO",
    json_format: bool = True,
    log_file: str | None = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatter (True for production)
        log_file: Optional file path for log output
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.FileHandler(log_file) if log_file else logging.StreamHandler()

    # Set formatter
    if json_format:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] %(message)s"))

    # Add request ID filter
    handler.addFilter(RequestIdFilter())

    root_logger.addHandler(handler)

    # Configure specific loggers
    loggers_config = {
        "cms": log_level,
        "cms.access": log_level,
        "uvicorn": "WARNING",
        "uvicorn.access": "WARNING",
        "sqlalchemy.engine": "WARNING",
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get("")
