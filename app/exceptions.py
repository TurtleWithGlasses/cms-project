"""
Custom Exception Classes for CMS Project

This module defines custom exceptions for better error handling and
consistent error responses across the application.

Error codes follow the format: CATEGORY_SPECIFIC_ERROR
- AUTH_*: Authentication and authorization errors
- RESOURCE_*: Resource not found errors
- VALIDATION_*: Input validation errors
- DB_*: Database operation errors
- SERVICE_*: Service layer errors
- RATE_*: Rate limiting errors
- FILE_*: File and media errors
"""

from enum import Enum
from typing import Any

from fastapi import status


class ErrorCode(str, Enum):
    """
    Standardized error codes for i18n support.

    These codes can be used by frontend applications to display
    localized error messages based on the user's language preference.
    """

    # Authentication & Authorization (AUTH_*)
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"  # nosec B105
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"  # nosec B105
    AUTH_PERMISSION_DENIED = "AUTH_PERMISSION_DENIED"
    AUTH_TWO_FACTOR_REQUIRED = "AUTH_TWO_FACTOR_REQUIRED"
    AUTH_TWO_FACTOR_INVALID = "AUTH_TWO_FACTOR_INVALID"
    AUTH_SESSION_EXPIRED = "AUTH_SESSION_EXPIRED"

    # Resource Not Found (RESOURCE_*)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_USER_NOT_FOUND = "RESOURCE_USER_NOT_FOUND"
    RESOURCE_CONTENT_NOT_FOUND = "RESOURCE_CONTENT_NOT_FOUND"
    RESOURCE_CATEGORY_NOT_FOUND = "RESOURCE_CATEGORY_NOT_FOUND"
    RESOURCE_ROLE_NOT_FOUND = "RESOURCE_ROLE_NOT_FOUND"
    RESOURCE_COMMENT_NOT_FOUND = "RESOURCE_COMMENT_NOT_FOUND"
    RESOURCE_MEDIA_NOT_FOUND = "RESOURCE_MEDIA_NOT_FOUND"
    RESOURCE_TEMPLATE_NOT_FOUND = "RESOURCE_TEMPLATE_NOT_FOUND"
    RESOURCE_TEAM_NOT_FOUND = "RESOURCE_TEAM_NOT_FOUND"
    RESOURCE_WEBHOOK_NOT_FOUND = "RESOURCE_WEBHOOK_NOT_FOUND"
    RESOURCE_API_KEY_NOT_FOUND = "RESOURCE_API_KEY_NOT_FOUND"

    # Validation & Business Logic (VALIDATION_*)
    VALIDATION_FAILED = "VALIDATION_FAILED"
    VALIDATION_DUPLICATE_RESOURCE = "VALIDATION_DUPLICATE_RESOURCE"
    VALIDATION_INVALID_STATUS_TRANSITION = "VALIDATION_INVALID_STATUS_TRANSITION"
    VALIDATION_INVALID_OPERATION = "VALIDATION_INVALID_OPERATION"
    VALIDATION_REQUIRED_FIELD = "VALIDATION_REQUIRED_FIELD"
    VALIDATION_INVALID_FORMAT = "VALIDATION_INVALID_FORMAT"
    VALIDATION_VALUE_TOO_LONG = "VALIDATION_VALUE_TOO_LONG"
    VALIDATION_VALUE_TOO_SHORT = "VALIDATION_VALUE_TOO_SHORT"

    # Database & Service (DB_*, SERVICE_*)
    DB_ERROR = "DB_ERROR"
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_TRANSACTION_FAILED = "DB_TRANSACTION_FAILED"
    SERVICE_ERROR = "SERVICE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    SERVICE_TIMEOUT = "SERVICE_TIMEOUT"

    # Rate Limiting & Security (RATE_*, SECURITY_*)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SECURITY_CSRF_FAILED = "SECURITY_CSRF_FAILED"
    SECURITY_BLOCKED = "SECURITY_BLOCKED"

    # File & Media (FILE_*)
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    FILE_TYPE_NOT_ALLOWED = "FILE_TYPE_NOT_ALLOWED"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_PROCESSING_FAILED = "FILE_PROCESSING_FAILED"

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class CMSError(Exception):
    """
    Base exception class for all CMS-related exceptions.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Machine-readable error code for i18n
        details: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


# ============================================================================
# Authentication & Authorization Exceptions
# ============================================================================


class AuthenticationError(CMSError):
    """Raised when authentication fails"""

    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: ErrorCode = ErrorCode.AUTH_FAILED,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            details=details or {},
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid"""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message=message, error_code=ErrorCode.AUTH_INVALID_CREDENTIALS)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, error_code=ErrorCode.AUTH_TOKEN_EXPIRED)


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid"""

    def __init__(self, message: str = "Invalid or malformed token"):
        super().__init__(message=message, error_code=ErrorCode.AUTH_TOKEN_INVALID)


class TwoFactorRequiredError(AuthenticationError):
    """Raised when 2FA verification is required"""

    def __init__(self, message: str = "Two-factor authentication required"):
        super().__init__(message=message, error_code=ErrorCode.AUTH_TWO_FACTOR_REQUIRED)


class TwoFactorInvalidError(AuthenticationError):
    """Raised when 2FA code is invalid"""

    def __init__(self, message: str = "Invalid two-factor authentication code"):
        super().__init__(message=message, error_code=ErrorCode.AUTH_TWO_FACTOR_INVALID)


class SessionExpiredError(AuthenticationError):
    """Raised when user session has expired"""

    def __init__(self, message: str = "Session has expired. Please log in again."):
        super().__init__(message=message, error_code=ErrorCode.AUTH_SESSION_EXPIRED)


class AuthorizationError(CMSError):
    """Raised when user lacks permission for an action"""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        required_permission: str | None = None,
    ):
        details = {"required_permission": required_permission} if required_permission else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.AUTH_PERMISSION_DENIED,
            details=details,
        )


# ============================================================================
# Resource Not Found Exceptions
# ============================================================================


class ResourceNotFoundError(CMSError):
    """Base class for resource not found errors"""

    def __init__(
        self,
        resource_type: str,
        resource_id: Any | None = None,
        error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
    ):
        message = f"{resource_type} not found"
        if resource_id is not None:
            message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
            details={"resource_type": resource_type, "resource_id": resource_id},
        )


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user is not found"""

    def __init__(self, user_id: Any | None = None):
        super().__init__(
            resource_type="User",
            resource_id=user_id,
            error_code=ErrorCode.RESOURCE_USER_NOT_FOUND,
        )


class ContentNotFoundError(ResourceNotFoundError):
    """Raised when content is not found"""

    def __init__(self, content_id: Any | None = None):
        super().__init__(
            resource_type="Content",
            resource_id=content_id,
            error_code=ErrorCode.RESOURCE_CONTENT_NOT_FOUND,
        )


class CategoryNotFoundError(ResourceNotFoundError):
    """Raised when a category is not found"""

    def __init__(self, category_id: Any | None = None):
        super().__init__(
            resource_type="Category",
            resource_id=category_id,
            error_code=ErrorCode.RESOURCE_CATEGORY_NOT_FOUND,
        )


class RoleNotFoundError(ResourceNotFoundError):
    """Raised when a role is not found"""

    def __init__(self, role_id: Any | None = None):
        super().__init__(
            resource_type="Role",
            resource_id=role_id,
            error_code=ErrorCode.RESOURCE_ROLE_NOT_FOUND,
        )


class CommentNotFoundError(ResourceNotFoundError):
    """Raised when a comment is not found"""

    def __init__(self, comment_id: Any | None = None):
        super().__init__(
            resource_type="Comment",
            resource_id=comment_id,
            error_code=ErrorCode.RESOURCE_COMMENT_NOT_FOUND,
        )


class MediaNotFoundError(ResourceNotFoundError):
    """Raised when media is not found"""

    def __init__(self, media_id: Any | None = None):
        super().__init__(
            resource_type="Media",
            resource_id=media_id,
            error_code=ErrorCode.RESOURCE_MEDIA_NOT_FOUND,
        )


class TemplateNotFoundError(ResourceNotFoundError):
    """Raised when a template is not found"""

    def __init__(self, template_id: Any | None = None):
        super().__init__(
            resource_type="Template",
            resource_id=template_id,
            error_code=ErrorCode.RESOURCE_TEMPLATE_NOT_FOUND,
        )


class TeamNotFoundError(ResourceNotFoundError):
    """Raised when a team is not found"""

    def __init__(self, team_id: Any | None = None):
        super().__init__(
            resource_type="Team",
            resource_id=team_id,
            error_code=ErrorCode.RESOURCE_TEAM_NOT_FOUND,
        )


class WebhookNotFoundError(ResourceNotFoundError):
    """Raised when a webhook is not found"""

    def __init__(self, webhook_id: Any | None = None):
        super().__init__(
            resource_type="Webhook",
            resource_id=webhook_id,
            error_code=ErrorCode.RESOURCE_WEBHOOK_NOT_FOUND,
        )


class APIKeyNotFoundError(ResourceNotFoundError):
    """Raised when an API key is not found"""

    def __init__(self, key_id: Any | None = None):
        super().__init__(
            resource_type="API Key",
            resource_id=key_id,
            error_code=ErrorCode.RESOURCE_API_KEY_NOT_FOUND,
        )


# ============================================================================
# Validation & Business Logic Exceptions
# ============================================================================


class ValidationError(CMSError):
    """Raised when input validation fails"""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        error_code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        details: dict[str, Any] | None = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=error_details,
        )


class DuplicateResourceError(CMSError):
    """Raised when attempting to create a duplicate resource"""

    def __init__(self, resource_type: str, field: str, value: Any):
        super().__init__(
            message=f"{resource_type} with {field} '{value}' already exists",
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.VALIDATION_DUPLICATE_RESOURCE,
            details={"resource_type": resource_type, "field": field, "value": value},
        )


class InvalidStatusTransitionError(CMSError):
    """Raised when an invalid status transition is attempted"""

    def __init__(self, current_status: str, target_status: str, resource_type: str = "Resource"):
        super().__init__(
            message=f"Cannot transition {resource_type} from '{current_status}' to '{target_status}'",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_INVALID_STATUS_TRANSITION,
            details={
                "resource_type": resource_type,
                "current_status": current_status,
                "target_status": target_status,
            },
        )


class InvalidOperationError(CMSError):
    """Raised when an operation is invalid in the current context"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.VALIDATION_INVALID_OPERATION,
            details=details or {},
        )


# ============================================================================
# Database & Service Exceptions
# ============================================================================


class DatabaseError(CMSError):
    """Raised when a database operation fails"""

    def __init__(
        self,
        message: str = "A database error occurred",
        operation: str | None = None,
        error_code: ErrorCode = ErrorCode.DB_ERROR,
    ):
        details = {"operation": operation} if operation else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""

    def __init__(self, message: str = "Failed to connect to database"):
        super().__init__(message=message, error_code=ErrorCode.DB_CONNECTION_FAILED)


class ServiceError(CMSError):
    """Raised when a service layer operation fails"""

    def __init__(
        self,
        message: str,
        service: str | None = None,
        error_code: ErrorCode = ErrorCode.SERVICE_ERROR,
    ):
        details = {"service": service} if service else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
        )


class ServiceUnavailableError(ServiceError):
    """Raised when a required service is unavailable"""

    def __init__(self, service: str, message: str | None = None):
        super().__init__(
            message=message or f"Service '{service}' is currently unavailable",
            service=service,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
        )


class ServiceTimeoutError(ServiceError):
    """Raised when a service operation times out"""

    def __init__(self, service: str, message: str | None = None):
        super().__init__(
            message=message or f"Service '{service}' operation timed out",
            service=service,
            error_code=ErrorCode.SERVICE_TIMEOUT,
        )


# ============================================================================
# Rate Limiting & Security Exceptions
# ============================================================================


class RateLimitExceededError(CMSError):
    """Raised when rate limit is exceeded"""

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: int | None = None,
    ):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details=details,
        )


class CSRFError(CMSError):
    """Raised when CSRF validation fails"""

    def __init__(self, message: str = "CSRF validation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.SECURITY_CSRF_FAILED,
        )


class SecurityBlockedError(CMSError):
    """Raised when request is blocked for security reasons"""

    def __init__(self, message: str = "Request blocked for security reasons"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.SECURITY_BLOCKED,
        )


# ============================================================================
# File & Media Exceptions
# ============================================================================


class FileUploadError(CMSError):
    """Raised when file upload fails"""

    def __init__(
        self,
        message: str = "File upload failed",
        filename: str | None = None,
        error_code: ErrorCode = ErrorCode.FILE_UPLOAD_FAILED,
    ):
        details = {"filename": filename} if filename else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=details,
        )


class InvalidFileTypeError(CMSError):
    """Raised when uploaded file type is not allowed"""

    def __init__(self, file_type: str, allowed_types: list[str]):
        super().__init__(
            message=f"File type '{file_type}' is not allowed",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.FILE_TYPE_NOT_ALLOWED,
            details={"file_type": file_type, "allowed_types": allowed_types},
        )


class FileTooLargeError(CMSError):
    """Raised when uploaded file exceeds size limit"""

    def __init__(self, file_size: int, max_size: int, filename: str | None = None):
        details = {
            "file_size": file_size,
            "max_size": max_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "max_size_mb": round(max_size / (1024 * 1024), 2),
        }
        if filename:
            details["filename"] = filename
        super().__init__(
            message=f"File size exceeds maximum allowed size of {max_size // (1024 * 1024)}MB",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=ErrorCode.FILE_TOO_LARGE,
            details=details,
        )


class FileNotFoundError(CMSError):
    """Raised when a file is not found on disk"""

    def __init__(self, filename: str | None = None):
        details = {"filename": filename} if filename else {}
        super().__init__(
            message="File not found",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.FILE_NOT_FOUND,
            details=details,
        )


class FileProcessingError(CMSError):
    """Raised when file processing fails"""

    def __init__(self, message: str = "Failed to process file", filename: str | None = None):
        details = {"filename": filename} if filename else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.FILE_PROCESSING_FAILED,
            details=details,
        )
