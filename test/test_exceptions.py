"""
Tests for custom exception classes

Tests exception initialization, messages, status codes, and details.
"""

from fastapi import status

from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CategoryNotFoundError,
    CMSError,
    ContentNotFoundError,
    CSRFError,
    DatabaseError,
    DuplicateResourceError,
    FileUploadError,
    InvalidCredentialsError,
    InvalidFileTypeError,
    InvalidOperationError,
    InvalidStatusTransitionError,
    InvalidTokenError,
    RateLimitExceededError,
    ResourceNotFoundError,
    RoleNotFoundError,
    ServiceError,
    TokenExpiredError,
    UserNotFoundError,
    ValidationError,
)


class TestCMSError:
    """Test base CMSError class"""

    def test_cms_exception_default(self):
        """Test CMSError with default values"""
        exc = CMSError("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc.details == {}

    def test_cms_exception_with_custom_status(self):
        """Test CMSError with custom status code"""
        exc = CMSError("Test error", status_code=status.HTTP_400_BAD_REQUEST)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_cms_exception_with_details(self):
        """Test CMSError with details"""
        details = {"key": "value", "count": 42}
        exc = CMSError("Test error", details=details)
        assert exc.details == details
        assert exc.details["key"] == "value"
        assert exc.details["count"] == 42


class TestAuthenticationExceptions:
    """Test authentication-related exceptions"""

    def test_authentication_error(self):
        """Test AuthenticationError"""
        exc = AuthenticationError()
        assert str(exc) == "Authentication failed"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message"""
        exc = AuthenticationError("Custom auth error")
        assert str(exc) == "Custom auth error"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_credentials_error(self):
        """Test InvalidCredentialsError"""
        exc = InvalidCredentialsError()
        assert str(exc) == "Invalid email or password"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_credentials_error_custom_message(self):
        """Test InvalidCredentialsError with custom message"""
        exc = InvalidCredentialsError("Wrong password")
        assert str(exc) == "Wrong password"

    def test_token_expired_error(self):
        """Test TokenExpiredError"""
        exc = TokenExpiredError()
        assert str(exc) == "Token has expired"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_error(self):
        """Test InvalidTokenError"""
        exc = InvalidTokenError()
        assert str(exc) == "Invalid or malformed token"
        assert exc.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthorizationExceptions:
    """Test authorization exceptions"""

    def test_authorization_error_default(self):
        """Test AuthorizationError with default message"""
        exc = AuthorizationError()
        assert "permission" in str(exc).lower()
        assert exc.status_code == status.HTTP_403_FORBIDDEN

    def test_authorization_error_with_permission(self):
        """Test AuthorizationError with required permission"""
        exc = AuthorizationError(required_permission="admin")
        assert exc.details["required_permission"] == "admin"

    def test_authorization_error_custom_message(self):
        """Test AuthorizationError with custom message"""
        exc = AuthorizationError("Admin only")
        assert str(exc) == "Admin only"


class TestResourceNotFoundExceptions:
    """Test resource not found exceptions"""

    def test_resource_not_found_without_id(self):
        """Test ResourceNotFoundError without resource ID"""
        exc = ResourceNotFoundError("Item")
        assert str(exc) == "Item not found"
        assert exc.status_code == status.HTTP_404_NOT_FOUND
        assert exc.details["resource_type"] == "Item"

    def test_resource_not_found_with_id(self):
        """Test ResourceNotFoundError with resource ID"""
        exc = ResourceNotFoundError("Item", resource_id=123)
        assert str(exc) == "Item with id '123' not found"
        assert exc.details["resource_id"] == 123

    def test_user_not_found_error(self):
        """Test UserNotFoundError"""
        exc = UserNotFoundError(user_id=42)
        assert "User" in str(exc)
        assert "42" in str(exc)
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_content_not_found_error(self):
        """Test ContentNotFoundError"""
        exc = ContentNotFoundError(content_id=100)
        assert "Content" in str(exc)
        assert "100" in str(exc)

    def test_category_not_found_error(self):
        """Test CategoryNotFoundError"""
        exc = CategoryNotFoundError(category_id=5)
        assert "Category" in str(exc)
        assert "5" in str(exc)

    def test_role_not_found_error(self):
        """Test RoleNotFoundError"""
        exc = RoleNotFoundError(role_id="admin")
        assert "Role" in str(exc)
        assert "admin" in str(exc)


class TestValidationExceptions:
    """Test validation and business logic exceptions"""

    def test_validation_error_simple(self):
        """Test ValidationError with simple message"""
        exc = ValidationError("Invalid input")
        assert str(exc) == "Invalid input"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_validation_error_with_field(self):
        """Test ValidationError with field name"""
        exc = ValidationError("Invalid email format", field="email")
        assert exc.details["field"] == "email"

    def test_validation_error_with_details(self):
        """Test ValidationError with additional details"""
        details = {"min_length": 8, "max_length": 100}
        exc = ValidationError("Password too short", field="password", details=details)
        assert exc.details["field"] == "password"
        assert exc.details["min_length"] == 8

    def test_duplicate_resource_error(self):
        """Test DuplicateResourceError"""
        exc = DuplicateResourceError("User", "email", "test@example.com")
        assert "User" in str(exc)
        assert "email" in str(exc)
        assert "test@example.com" in str(exc)
        assert exc.status_code == status.HTTP_409_CONFLICT
        assert exc.details["resource_type"] == "User"
        assert exc.details["field"] == "email"
        assert exc.details["value"] == "test@example.com"

    def test_invalid_status_transition_error(self):
        """Test InvalidStatusTransitionError"""
        exc = InvalidStatusTransitionError("draft", "archived", "Content")
        assert "draft" in str(exc)
        assert "archived" in str(exc)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST
        assert exc.details["current_status"] == "draft"
        assert exc.details["target_status"] == "archived"

    def test_invalid_operation_error(self):
        """Test InvalidOperationError"""
        exc = InvalidOperationError("Cannot delete published content")
        assert "Cannot delete" in str(exc)
        assert exc.status_code == status.HTTP_400_BAD_REQUEST


class TestDatabaseExceptions:
    """Test database and service exceptions"""

    def test_database_error_default(self):
        """Test DatabaseError with default message"""
        exc = DatabaseError()
        assert "database error" in str(exc).lower()
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_database_error_with_operation(self):
        """Test DatabaseError with operation detail"""
        exc = DatabaseError("Connection failed", operation="connect")
        assert str(exc) == "Connection failed"
        assert exc.details["operation"] == "connect"

    def test_service_error_default(self):
        """Test ServiceError"""
        exc = ServiceError("Service unavailable")
        assert str(exc) == "Service unavailable"
        assert exc.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_service_error_with_service_name(self):
        """Test ServiceError with service name"""
        exc = ServiceError("Email send failed", service="EmailService")
        assert exc.details["service"] == "EmailService"


class TestSecurityExceptions:
    """Test rate limiting and security exceptions"""

    def test_rate_limit_exceeded_error(self):
        """Test RateLimitExceededError"""
        exc = RateLimitExceededError()
        assert "rate limit" in str(exc).lower()
        assert exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_rate_limit_exceeded_custom_message(self):
        """Test RateLimitExceededError with custom message"""
        exc = RateLimitExceededError("Too many requests from this IP")
        assert "Too many requests" in str(exc)

    def test_csrf_error(self):
        """Test CSRFError"""
        exc = CSRFError()
        assert "CSRF" in str(exc)
        assert exc.status_code == status.HTTP_403_FORBIDDEN


class TestFileExceptions:
    """Test file and media exceptions"""

    def test_file_upload_error_default(self):
        """Test FileUploadError with default message"""
        exc = FileUploadError()
        assert "upload failed" in str(exc).lower()
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_file_upload_error_with_filename(self):
        """Test FileUploadError with filename"""
        exc = FileUploadError("File too large", filename="image.jpg")
        assert str(exc) == "File too large"
        assert exc.details["filename"] == "image.jpg"

    def test_invalid_file_type_error(self):
        """Test InvalidFileTypeError"""
        allowed = ["jpg", "png", "gif"]
        exc = InvalidFileTypeError("pdf", allowed)
        assert "pdf" in str(exc)
        assert exc.details["file_type"] == "pdf"
        assert exc.details["allowed_types"] == allowed
        assert exc.status_code == status.HTTP_400_BAD_REQUEST


class TestExceptionInheritance:
    """Test exception inheritance hierarchy"""

    def test_all_exceptions_inherit_from_cms_exception(self):
        """Test that all custom exceptions inherit from CMSError"""
        exceptions = [
            AuthenticationError(),
            AuthorizationError(),
            InvalidCredentialsError(),
            TokenExpiredError(),
            InvalidTokenError(),
            ResourceNotFoundError("Test"),
            UserNotFoundError(),
            ContentNotFoundError(),
            CategoryNotFoundError(),
            RoleNotFoundError(),
            ValidationError("Test"),
            DuplicateResourceError("Test", "field", "value"),
            InvalidStatusTransitionError("a", "b"),
            InvalidOperationError("Test"),
            DatabaseError(),
            ServiceError("Test"),
            RateLimitExceededError(),
            CSRFError(),
            FileUploadError(),
            InvalidFileTypeError("pdf", ["jpg"]),
        ]

        for exc in exceptions:
            assert isinstance(exc, CMSError)
            assert isinstance(exc, Exception)

    def test_authentication_exceptions_inherit_correctly(self):
        """Test authentication exception inheritance"""
        assert isinstance(InvalidCredentialsError(), AuthenticationError)
        assert isinstance(TokenExpiredError(), AuthenticationError)
        assert isinstance(InvalidTokenError(), AuthenticationError)

    def test_resource_not_found_exceptions_inherit_correctly(self):
        """Test resource not found exception inheritance"""
        assert isinstance(UserNotFoundError(), ResourceNotFoundError)
        assert isinstance(ContentNotFoundError(), ResourceNotFoundError)
        assert isinstance(CategoryNotFoundError(), ResourceNotFoundError)
        assert isinstance(RoleNotFoundError(), ResourceNotFoundError)
