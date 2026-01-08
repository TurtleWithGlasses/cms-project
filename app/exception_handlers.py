"""
Global Exception Handlers for CMS Project

This module provides centralized exception handling for consistent
error responses across the application.
"""

import logging
from typing import Any, Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import CMSException

logger = logging.getLogger(__name__)


def create_error_response(
    status_code: int, message: str, details: dict[str, Any] | None = None, path: str | None = None
) -> JSONResponse:
    """
    Create a standardized error response

    Args:
        status_code: HTTP status code
        message: Error message
        details: Additional error details
        path: Request path that caused the error

    Returns:
        JSONResponse with standardized error format
    """
    error_response = {"error": {"status_code": status_code, "message": message, "type": get_error_type(status_code)}}

    if details:
        error_response["error"]["details"] = details

    if path:
        error_response["error"]["path"] = path

    return JSONResponse(status_code=status_code, content=error_response)


def get_error_type(status_code: int) -> str:
    """Get a human-readable error type based on status code"""
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


async def cms_exception_handler(request: Request, exc: CMSException) -> JSONResponse:
    """
    Handle custom CMS exceptions

    Args:
        request: The request that caused the exception
        exc: The CMSException instance

    Returns:
        JSONResponse with error details
    """
    logger.error(
        f"CMSException: {exc.message}",
        extra={"status_code": exc.status_code, "path": request.url.path, "details": exc.details},
    )

    return create_error_response(
        status_code=exc.status_code,
        message=exc.message,
        details=exc.details if exc.details else None,
        path=request.url.path,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle standard HTTP exceptions

    Args:
        request: The request that caused the exception
        exc: The HTTPException instance

    Returns:
        JSONResponse with error details
    """
    logger.warning(f"HTTPException: {exc.detail}", extra={"status_code": exc.status_code, "path": request.url.path})

    return create_error_response(status_code=exc.status_code, message=str(exc.detail), path=request.url.path)


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors

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
        details={"validation_errors": errors},
        path=request.url.path,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions

    Args:
        request: The request that caused the exception
        exc: The exception instance

    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        f"Unhandled exception: {str(exc)}", exc_info=True, extra={"path": request.url.path, "method": request.method}
    )

    # Don't expose internal error details in production
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred. Please try again later.",
        path=request.url.path,
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with the FastAPI app

    Args:
        app: The FastAPI application instance
    """
    # Custom CMS exceptions
    app.add_exception_handler(CMSException, cms_exception_handler)

    # Standard HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info("Exception handlers registered successfully")
