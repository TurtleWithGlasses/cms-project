"""
Custom Exception Classes for CMS Project

This module defines custom exceptions for better error handling and
consistent error responses across the application.
"""

from typing import Any

from fastapi import status


class CMSException(Exception):
    """Base exception class for all CMS-related exceptions"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# ============================================================================
# Authentication & Authorization Exceptions
# ============================================================================


class AuthenticationError(CMSException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_401_UNAUTHORIZED, details=details or {})


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid"""

    def __init__(self, message: str = "Invalid or malformed token"):
        super().__init__(message=message)


class AuthorizationError(CMSException):
    """Raised when user lacks permission for an action"""

    def __init__(
        self, message: str = "You do not have permission to perform this action", required_permission: str | None = None
    ):
        details = {"required_permission": required_permission} if required_permission else {}
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN, details=details)


# ============================================================================
# Resource Not Found Exceptions
# ============================================================================


class ResourceNotFoundError(CMSException):
    """Base class for resource not found errors"""

    def __init__(self, resource_type: str, resource_id: Any | None = None):
        message = f"{resource_type} not found"
        if resource_id is not None:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user is not found"""

    def __init__(self, user_id: Any | None = None):
        super().__init__(resource_type="User", resource_id=user_id)


class ContentNotFoundError(ResourceNotFoundError):
    """Raised when content is not found"""

    def __init__(self, content_id: Any | None = None):
        super().__init__(resource_type="Content", resource_id=content_id)


class CategoryNotFoundError(ResourceNotFoundError):
    """Raised when a category is not found"""

    def __init__(self, category_id: Any | None = None):
        super().__init__(resource_type="Category", resource_id=category_id)


class RoleNotFoundError(ResourceNotFoundError):
    """Raised when a role is not found"""

    def __init__(self, role_id: Any | None = None):
        super().__init__(resource_type="Role", resource_id=role_id)


# ============================================================================
# Validation & Business Logic Exceptions
# ============================================================================


class ValidationError(CMSException):
    """Raised when input validation fails"""

    def __init__(self, message: str, field: str | None = None, details: dict[str, Any] | None = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=error_details)


class DuplicateResourceError(CMSException):
    """Raised when attempting to create a duplicate resource"""

    def __init__(self, resource_type: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_type} with {field} '{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            details={"resource_type": resource_type, "field": field, "value": value},
        )


class InvalidStatusTransitionError(CMSException):
    """Raised when an invalid status transition is attempted"""

    def __init__(self, current_status: str, target_status: str, resource_type: str = "Resource"):
        super().__init__(
            message=f"Cannot transition {resource_type} from '{current_status}' to '{target_status}'",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"resource_type": resource_type, "current_status": current_status, "target_status": target_status},
        )


class InvalidOperationError(CMSException):
    """Raised when an operation is invalid in the current context"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details or {})


# ============================================================================
# Database & Service Exceptions
# ============================================================================


class DatabaseError(CMSException):
    """Raised when a database operation fails"""

    def __init__(self, message: str = "A database error occurred", operation: str | None = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


class ServiceError(CMSException):
    """Raised when a service layer operation fails"""

    def __init__(self, message: str, service: str | None = None):
        details = {"service": service} if service else {}
        super().__init__(message=message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)


# ============================================================================
# Rate Limiting & Security Exceptions
# ============================================================================


class RateLimitExceededError(CMSException):
    """Raised when rate limit is exceeded"""

    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(message=message, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class CSRFError(CMSException):
    """Raised when CSRF validation fails"""

    def __init__(self, message: str = "CSRF validation failed"):
        super().__init__(message=message, status_code=status.HTTP_403_FORBIDDEN)


# ============================================================================
# File & Media Exceptions
# ============================================================================


class FileUploadError(CMSException):
    """Raised when file upload fails"""

    def __init__(self, message: str = "File upload failed", filename: str | None = None):
        details = {"filename": filename} if filename else {}
        super().__init__(message=message, status_code=status.HTTP_400_BAD_REQUEST, details=details)


class InvalidFileTypeError(CMSException):
    """Raised when uploaded file type is not allowed"""

    def __init__(self, file_type: str, allowed_types: list[str]):
        super().__init__(
            message=f"File type '{file_type}' is not allowed",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"file_type": file_type, "allowed_types": allowed_types},
        )
