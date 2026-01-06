"""
Tests for password reset schemas

Tests password reset request, confirm, and response schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.password_reset import (
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
)


class TestPasswordResetRequest:
    """Test PasswordResetRequest schema"""

    def test_password_reset_request_with_valid_email(self):
        """Test password reset request with valid email"""
        data = {"email": "test@example.com"}
        request = PasswordResetRequest(**data)
        assert request.email == "test@example.com"

    def test_password_reset_request_requires_email(self):
        """Test that email is required"""
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetRequest(**data)
        assert "email" in str(exc_info.value).lower()

    def test_password_reset_request_validates_email_format(self):
        """Test that email format is validated"""
        data = {"email": "invalid-email"}
        with pytest.raises(ValidationError):
            PasswordResetRequest(**data)

    def test_password_reset_request_accepts_various_email_formats(self):
        """Test various valid email formats"""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@sub.example.com",
        ]
        for email in valid_emails:
            data = {"email": email}
            request = PasswordResetRequest(**data)
            assert request.email == email


class TestPasswordResetConfirm:
    """Test PasswordResetConfirm schema"""

    def test_password_reset_confirm_with_matching_passwords(self):
        """Test password reset confirm with matching passwords"""
        data = {
            "token": "valid-token-string",
            "new_password": "newpassword123",  # nosec B106
            "confirm_password": "newpassword123",  # nosec B106
        }
        confirm = PasswordResetConfirm(**data)
        assert confirm.token == "valid-token-string"
        assert confirm.new_password == "newpassword123"  # nosec B106
        assert confirm.confirm_password == "newpassword123"  # nosec B106

    def test_password_reset_confirm_with_mismatched_passwords(self):
        """Test that mismatched passwords raise validation error"""
        data = {
            "token": "valid-token-string",
            "new_password": "newpassword123",  # nosec B106
            "confirm_password": "differentpassword",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        assert "do not match" in str(exc_info.value).lower()

    def test_password_reset_confirm_requires_token(self):
        """Test that token is required"""
        data = {
            "new_password": "newpassword123",  # nosec B106
            "confirm_password": "newpassword123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        assert "token" in str(exc_info.value).lower()

    def test_password_reset_confirm_requires_new_password(self):
        """Test that new_password is required"""
        data = {
            "token": "valid-token-string",
            "confirm_password": "newpassword123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        assert "new_password" in str(exc_info.value).lower()

    def test_password_reset_confirm_requires_confirm_password(self):
        """Test that confirm_password is required"""
        data = {
            "token": "valid-token-string",
            "new_password": "newpassword123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetConfirm(**data)
        assert "confirm_password" in str(exc_info.value).lower()

    def test_password_reset_confirm_enforces_min_password_length(self):
        """Test that minimum password length is enforced"""
        data = {
            "token": "valid-token-string",
            "new_password": "short",  # Less than 8 chars  # nosec B106
            "confirm_password": "short",  # nosec B106
        }
        with pytest.raises(ValidationError):
            PasswordResetConfirm(**data)

    def test_password_reset_confirm_enforces_max_password_length(self):
        """Test that maximum password length is enforced"""
        long_password = "a" * 101  # More than 100 chars
        data = {
            "token": "valid-token-string",
            "new_password": long_password,
            "confirm_password": long_password,
        }
        with pytest.raises(ValidationError):
            PasswordResetConfirm(**data)

    def test_password_reset_confirm_token_cannot_be_empty(self):
        """Test that token cannot be empty string"""
        data = {
            "token": "",
            "new_password": "newpassword123",  # nosec B106
            "confirm_password": "newpassword123",  # nosec B106
        }
        with pytest.raises(ValidationError):
            PasswordResetConfirm(**data)

    def test_password_reset_confirm_with_special_characters_in_password(self):
        """Test that passwords with special characters are accepted"""
        data = {
            "token": "valid-token-string",
            "new_password": "P@ssw0rd!#$",  # nosec B106
            "confirm_password": "P@ssw0rd!#$",  # nosec B106
        }
        confirm = PasswordResetConfirm(**data)
        assert confirm.new_password == "P@ssw0rd!#$"  # nosec B106


class TestPasswordResetResponse:
    """Test PasswordResetResponse schema"""

    def test_password_reset_response_with_success(self):
        """Test password reset response with success"""
        data = {
            "message": "Password reset email sent successfully",
            "success": True,
        }
        response = PasswordResetResponse(**data)
        assert response.message == "Password reset email sent successfully"
        assert response.success is True

    def test_password_reset_response_with_failure(self):
        """Test password reset response with failure"""
        data = {
            "message": "User not found",
            "success": False,
        }
        response = PasswordResetResponse(**data)
        assert response.message == "User not found"
        assert response.success is False

    def test_password_reset_response_defaults_to_success(self):
        """Test that success defaults to True"""
        data = {"message": "Password reset successful"}
        response = PasswordResetResponse(**data)
        assert response.success is True

    def test_password_reset_response_requires_message(self):
        """Test that message is required"""
        data = {"success": True}
        with pytest.raises(ValidationError) as exc_info:
            PasswordResetResponse(**data)
        assert "message" in str(exc_info.value).lower()

    def test_password_reset_response_various_messages(self):
        """Test various response messages"""
        messages = [
            "Password reset link sent to your email",
            "Password has been reset successfully",
            "Invalid or expired reset token",
            "User account not found",
        ]
        for msg in messages:
            data = {"message": msg}
            response = PasswordResetResponse(**data)
            assert response.message == msg


class TestPasswordResetSchemaIntegration:
    """Test password reset schema integration scenarios"""

    def test_full_password_reset_flow(self):
        """Test complete password reset workflow"""
        # Step 1: Request password reset
        request = PasswordResetRequest(email="user@example.com")
        assert request.email == "user@example.com"

        # Step 2: Confirm with token and new password
        confirm = PasswordResetConfirm(
            token="reset-token-123",
            new_password="newsecurepassword",  # nosec B106
            confirm_password="newsecurepassword",  # nosec B106
        )
        assert confirm.token == "reset-token-123"

        # Step 3: Get success response
        response = PasswordResetResponse(message="Password reset successful", success=True)
        assert response.success is True

    def test_password_complexity_requirements(self):
        """Test various password complexities"""
        test_passwords = [
            "SimplePass123",  # nosec B106
            "Complex!P@ss#123",  # nosec B106
            "VeryLongPasswordThatIsStillValid123",  # nosec B106
        ]
        for password in test_passwords:
            data = {
                "token": "token",
                "new_password": password,
                "confirm_password": password,
            }
            confirm = PasswordResetConfirm(**data)
            assert confirm.new_password == password
