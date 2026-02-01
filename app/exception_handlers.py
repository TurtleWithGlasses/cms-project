"""
Global Exception Handlers for CMS Project

This module provides centralized exception handling for consistent
error responses across the application.

Error Response Format:
{
    "error": {
        "status_code": 404,
        "error_code": "RESOURCE_USER_NOT_FOUND",
        "message": "User with id '123' not found",
        "type": "Not Found",
        "details": {"resource_type": "User", "resource_id": 123},
        "path": "/api/v1/users/123"
    }
}

The `error_code` field is a machine-readable code that can be used
by frontend applications for i18n/localization purposes.
"""

import logging
from typing import Any, Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import CMSError, ErrorCode

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int,
    message: str,
    error_code: str | ErrorCode | None = None,
    details: dict[str, Any] | None = None,
    path: str | None = None,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        message: Human-readable error message
        error_code: Machine-readable error code for i18n
        details: Additional error details
        path: Request path that caused the error

    Returns:
        JSONResponse with standardized error format
    """
    error_response: dict[str, Any] = {
        "error": {
            "status_code": status_code,
            "message": message,
            "type": get_error_type(status_code),
        }
    }

    # Add error_code if provided
    if error_code:
        error_response["error"]["error_code"] = error_code.value if isinstance(error_code, ErrorCode) else error_code

    if details:
        error_response["error"]["details"] = details

    if path:
        error_response["error"]["path"] = path

    return JSONResponse(status_code=status_code, content=error_response)


def get_error_type(status_code: int) -> str:
    """Get a human-readable error type based on status code."""
    error_types = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Validation Error",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }
    return error_types.get(status_code, "Error")


def get_http_error_code(status_code: int) -> str:
    """Map HTTP status codes to error codes for HTTPException."""
    error_code_map = {
        400: ErrorCode.VALIDATION_FAILED.value,
        401: ErrorCode.AUTH_FAILED.value,
        403: ErrorCode.AUTH_PERMISSION_DENIED.value,
        404: ErrorCode.RESOURCE_NOT_FOUND.value,
        409: ErrorCode.VALIDATION_DUPLICATE_RESOURCE.value,
        422: ErrorCode.VALIDATION_FAILED.value,
        429: ErrorCode.RATE_LIMIT_EXCEEDED.value,
        500: ErrorCode.INTERNAL_ERROR.value,
        502: ErrorCode.SERVICE_UNAVAILABLE.value,
        503: ErrorCode.SERVICE_UNAVAILABLE.value,
    }
    return error_code_map.get(status_code, ErrorCode.UNKNOWN_ERROR.value)


async def cms_exception_handler(request: Request, exc: CMSError) -> JSONResponse:
    """
    Handle custom CMS exceptions.

    Args:
        request: The request that caused the exception
        exc: The CMSError instance

    Returns:
        JSONResponse with error details including error_code for i18n
    """
    logger.error(
        f"CMSError: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.error_code.value,
            "path": request.url.path,
            "details": exc.details,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details if exc.details else None,
        path=request.url.path,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle standard HTTP exceptions.

    Args:
        request: The request that caused the exception
        exc: The HTTPException instance

    Returns:
        JSONResponse with error details, or index.html for SPA routes
    """
    # For 404 errors on non-API routes, serve the SPA
    if exc.status_code == 404:
        path = request.url.path
        if not path.startswith("/api/") and not path.startswith("/auth/"):
            from pathlib import Path

            from fastapi.responses import FileResponse

            frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"
            index_path = frontend_dir / "index.html"
            if index_path.exists():
                return FileResponse(index_path)

    logger.warning(
        f"HTTPException: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )

    return create_error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        error_code=get_http_error_code(exc.status_code),
        path=request.url.path,
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: The request that caused the exception
        exc: The validation error

    Returns:
        JSONResponse with validation error details
    """
    errors = []

    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            errors.append({"field": field, "message": error["msg"], "type": error["type"]})
    else:
        # PydanticValidationError
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({"field": field, "message": error["msg"], "type": error["type"]})

    logger.warning(f"Validation error on {request.url.path}", extra={"errors": errors})

    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        error_code=ErrorCode.VALIDATION_FAILED,
        details={"validation_errors": errors},
        path=request.url.path,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions.

    Args:
        request: The request that caused the exception
        exc: The exception instance

    Returns:
        JSONResponse with generic error message (internal details not exposed)
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path, "method": request.method},
    )

    # Don't expose internal error details in production
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred. Please try again later.",
        error_code=ErrorCode.INTERNAL_ERROR,
        path=request.url.path,
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: The FastAPI application instance
    """
    # Custom CMS exceptions
    app.add_exception_handler(CMSError, cms_exception_handler)

    # Standard HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("Exception handlers registered successfully")
