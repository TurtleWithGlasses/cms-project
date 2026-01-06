"""
Tests for user schemas

Tests user creation, update, and response schemas with field validators.
"""

import pytest
from pydantic import ValidationError

from app.schemas.user import (
    RoleEnum,
    RoleResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)


class TestUserCreate:
    """Test UserCreate schema"""

    def test_user_create_with_valid_data(self):
        """Test creating user with valid data"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        user = UserCreate(**data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "password123"  # nosec B106

    def test_user_create_sanitizes_username(self):
        """Test that username is sanitized"""
        data = {
            "username": "<script>testuser</script>",
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        user = UserCreate(**data)
        # Username should be sanitized
        assert "<script>" not in user.username

    def test_user_create_sanitizes_email(self):
        """Test that email is sanitized"""
        data = {
            "username": "testuser",
            "email": "  test@example.com  ",
            "password": "password123",  # nosec B106
        }
        user = UserCreate(**data)
        # Email should be sanitized (trimmed)
        assert user.email == "test@example.com"

    def test_user_create_username_too_short_after_sanitization(self):
        """Test that username validator rejects too short usernames after sanitization"""
        data = {
            "username": "<b>ab</b>",  # Only 2 chars after sanitization
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "at least 3 characters" in str(exc_info.value).lower()

    def test_user_create_requires_username(self):
        """Test that username is required"""
        data = {
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "username" in str(exc_info.value).lower()

    def test_user_create_requires_email(self):
        """Test that email is required"""
        data = {
            "username": "testuser",
            "password": "password123",  # nosec B106
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "email" in str(exc_info.value).lower()

    def test_user_create_requires_password(self):
        """Test that password is required"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
        }
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(**data)
        assert "password" in str(exc_info.value).lower()

    def test_user_create_username_min_length(self):
        """Test username minimum length validation"""
        data = {
            "username": "ab",  # Too short
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        with pytest.raises(ValidationError):
            UserCreate(**data)

    def test_user_create_password_min_length(self):
        """Test password minimum length validation"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "12345",  # Too short (< 6)  # nosec B106
        }
        with pytest.raises(ValidationError):
            UserCreate(**data)


class TestUserUpdate:
    """Test UserUpdate schema"""

    def test_user_update_with_all_fields(self):
        """Test updating user with all fields"""
        data = {
            "username": "newusername",
            "email": "newemail@example.com",
            "password": "newpassword123",  # nosec B106
        }
        user = UserUpdate(**data)
        assert user.username == "newusername"
        assert user.email == "newemail@example.com"
        assert user.password == "newpassword123"  # nosec B106

    def test_user_update_with_no_fields(self):
        """Test updating user with no fields"""
        data = {}
        user = UserUpdate(**data)
        assert user.username is None
        assert user.email is None
        assert user.password is None

    def test_user_update_partial_update(self):
        """Test partial user update"""
        data = {"username": "newusername"}
        user = UserUpdate(**data)
        assert user.username == "newusername"
        assert user.email is None
        assert user.password is None

    def test_user_update_sanitizes_username_when_none(self):
        """Test that None username passes through validator"""
        data = {"username": None}
        user = UserUpdate(**data)
        assert user.username is None

    def test_user_update_sanitizes_username_when_provided(self):
        """Test that username is sanitized when provided"""
        data = {"username": "<b>testuser</b>"}
        user = UserUpdate(**data)
        assert "<b>" not in user.username

    def test_user_update_username_too_short_after_sanitization(self):
        """Test that username validator rejects too short usernames after sanitization"""
        data = {"username": "<script>ab</script>"}  # Only 2 chars after sanitization
        with pytest.raises(ValidationError) as exc_info:
            UserUpdate(**data)
        assert "at least 3 characters" in str(exc_info.value).lower()

    def test_user_update_sanitizes_email_when_none(self):
        """Test that None email passes through validator"""
        data = {"email": None}
        user = UserUpdate(**data)
        assert user.email is None

    def test_user_update_sanitizes_email_when_provided(self):
        """Test that email is sanitized when provided"""
        data = {"email": "  test@example.com  "}
        user = UserUpdate(**data)
        assert user.email == "test@example.com"


class TestUserResponse:
    """Test UserResponse schema"""

    def test_user_response_with_all_fields(self):
        """Test user response with all fields"""
        data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "role": "user",
        }
        user = UserResponse(**data)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"

    def test_user_response_requires_all_fields(self):
        """Test that all fields are required"""
        data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            # Missing role
        }
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(**data)
        assert "role" in str(exc_info.value).lower()


class TestRoleEnum:
    """Test RoleEnum"""

    def test_role_enum_values(self):
        """Test that role enum has expected values"""
        assert RoleEnum.admin == "admin"
        assert RoleEnum.user == "user"
        assert RoleEnum.manager == "manager"
        assert RoleEnum.superadmin == "superadmin"

    def test_role_enum_is_string(self):
        """Test that role enum values are strings"""
        assert isinstance(RoleEnum.admin, str)
        assert isinstance(RoleEnum.user, str)


class TestRoleUpdate:
    """Test RoleUpdate schema"""

    def test_role_update_with_valid_role(self):
        """Test role update with valid role"""
        data = {"role": RoleEnum.admin}
        role = RoleUpdate(**data)
        assert role.role == RoleEnum.admin

    def test_role_update_with_string_role(self):
        """Test role update with string role value"""
        data = {"role": "admin"}
        role = RoleUpdate(**data)
        assert role.role == RoleEnum.admin

    def test_role_update_with_all_roles(self):
        """Test role update with all valid roles"""
        for role_value in ["admin", "user", "manager", "superadmin"]:
            data = {"role": role_value}
            role = RoleUpdate(**data)
            assert role.role.value == role_value

    def test_role_update_requires_role(self):
        """Test that role is required"""
        data = {}
        with pytest.raises(ValidationError) as exc_info:
            RoleUpdate(**data)
        assert "role" in str(exc_info.value).lower()

    def test_role_update_rejects_invalid_role(self):
        """Test that invalid role is rejected"""
        data = {"role": "invalid_role"}
        with pytest.raises(ValidationError):
            RoleUpdate(**data)


class TestRoleResponse:
    """Test RoleResponse schema"""

    def test_role_response_with_all_fields(self):
        """Test role response with all fields"""
        data = {
            "id": 1,
            "name": "admin",
            "description": "Administrator role",
        }
        role = RoleResponse(**data)
        assert role.id == 1
        assert role.name == "admin"
        assert role.description == "Administrator role"

    def test_role_response_with_none_description(self):
        """Test role response with None description"""
        data = {
            "id": 1,
            "name": "admin",
            "description": None,
        }
        role = RoleResponse(**data)
        assert role.description is None

    def test_role_response_requires_id(self):
        """Test that id is required"""
        data = {
            "name": "admin",
            "description": "Administrator role",
        }
        with pytest.raises(ValidationError) as exc_info:
            RoleResponse(**data)
        assert "id" in str(exc_info.value).lower()


class TestUserSchemaIntegration:
    """Test user schema integration scenarios"""

    def test_create_and_update_workflow(self):
        """Test creating then updating a user"""
        # Create user
        create_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",  # nosec B106
        }
        user = UserCreate(**create_data)

        # Update user
        update_data = {
            "username": "updateduser",
            "email": "updated@example.com",
        }
        updated = UserUpdate(**update_data)

        assert user.username == "testuser"
        assert updated.username == "updateduser"

    def test_username_sanitization_consistency(self):
        """Test that username sanitization is consistent across schemas"""
        test_username = "<script>testuser</script>"

        create = UserCreate(
            username=test_username,
            email="test@example.com",
            password="password123",  # nosec B106
        )
        update = UserUpdate(username=test_username)

        # Both should sanitize the same way
        assert create.username == update.username
        assert "<script>" not in create.username
