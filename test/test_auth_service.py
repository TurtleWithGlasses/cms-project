"""
Tests for authentication service functions

Tests user authentication and registration with mocked database.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.auth import hash_password
from app.models.user import Role, User
from app.services.auth_service import authenticate_user, register_user


class TestAuthenticateUser:
    """Test user authentication"""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        # Create mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("password123"),  # nosec B106
            role_id=1,
        )

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication
        result = await authenticate_user("test@example.com", "password123", mock_db)  # nosec B106

        assert result == mock_user
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        # Create mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("password123"),  # nosec B106
            role_id=1,
        )

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication with wrong password
        with pytest.raises(HTTPException) as exc_info:
            await authenticate_user("test@example.com", "wrongpassword", mock_db)

        assert exc_info.value.status_code == 401
        assert "invalid credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        # Mock database session - no user found
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication
        with pytest.raises(HTTPException) as exc_info:
            await authenticate_user("nonexistent@example.com", "password123", mock_db)  # nosec B106

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticate_user_empty_password(self):
        """Test authentication with empty password"""
        # Create mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            username="testuser",
            hashed_password=hash_password("password123"),  # nosec B106
            role_id=1,
        )

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = mock_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test authentication with empty password
        with pytest.raises(HTTPException) as exc_info:
            await authenticate_user("test@example.com", "", mock_db)

        assert exc_info.value.status_code == 401


class TestRegisterUser:
    """Test user registration"""

    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Test successful user registration"""
        # Mock role
        mock_role = Role(id=1, name="user", permissions=[])

        # Mock database session
        mock_db = AsyncMock()

        # First execute: check if email exists (returns None - email available)
        mock_email_result = MagicMock()
        mock_email_result.scalars().first.return_value = None

        # Second execute: get default role
        mock_role_result = MagicMock()
        mock_role_result.scalars().first.return_value = mock_role

        # Configure execute to return different results
        mock_db.execute = AsyncMock(side_effect=[mock_email_result, mock_role_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Test registration
        result = await register_user("new@example.com", "newuser", "password123", mock_db)  # nosec B106

        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # Verify user was created
        added_user = mock_db.add.call_args[0][0]
        assert added_user.email == "new@example.com"
        assert added_user.username == "newuser"
        assert added_user.role_id == mock_role.id

    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(self):
        """Test registration with existing email"""
        # Mock existing user
        existing_user = User(id=1, email="existing@example.com", username="existing", hashed_password="hash", role_id=1)

        # Mock database session
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = existing_user
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test registration
        with pytest.raises(HTTPException) as exc_info:
            await register_user("existing@example.com", "newuser", "password123", mock_db)  # nosec B106

        assert exc_info.value.status_code == 400
        assert "already registered" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_register_user_default_role_not_found(self):
        """Test registration when default role doesn't exist"""
        # Mock database session
        mock_db = AsyncMock()

        # First execute: check if email exists (returns None - email available)
        mock_email_result = MagicMock()
        mock_email_result.scalars().first.return_value = None

        # Second execute: get default role (returns None - role not found)
        mock_role_result = MagicMock()
        mock_role_result.scalars().first.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_email_result, mock_role_result])

        # Test registration
        with pytest.raises(HTTPException) as exc_info:
            await register_user("new@example.com", "newuser", "password123", mock_db)  # nosec B106

        assert exc_info.value.status_code == 500
        assert "default role" in exc_info.value.detail.lower()
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_register_user_password_is_hashed(self):
        """Test that password is properly hashed during registration"""
        # Mock role
        mock_role = Role(id=1, name="user", permissions=[])

        # Mock database session
        mock_db = AsyncMock()

        mock_email_result = MagicMock()
        mock_email_result.scalars().first.return_value = None

        mock_role_result = MagicMock()
        mock_role_result.scalars().first.return_value = mock_role

        mock_db.execute = AsyncMock(side_effect=[mock_email_result, mock_role_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Test registration
        plain_password = "mySecurePassword123"  # nosec B106
        await register_user("new@example.com", "newuser", plain_password, mock_db)

        # Verify password was hashed
        added_user = mock_db.add.call_args[0][0]
        assert added_user.hashed_password != plain_password
        assert len(added_user.hashed_password) > len(plain_password)

    @pytest.mark.asyncio
    async def test_register_user_with_special_characters(self):
        """Test registration with special characters in username and email"""
        # Mock role
        mock_role = Role(id=1, name="user", permissions=[])

        # Mock database session
        mock_db = AsyncMock()

        mock_email_result = MagicMock()
        mock_email_result.scalars().first.return_value = None

        mock_role_result = MagicMock()
        mock_role_result.scalars().first.return_value = mock_role

        mock_db.execute = AsyncMock(side_effect=[mock_email_result, mock_role_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Test registration with special characters
        await register_user("test+tag@example.com", "user_name-123", "password123", mock_db)  # nosec B106

        # Verify user was created with special characters
        added_user = mock_db.add.call_args[0][0]
        assert added_user.email == "test+tag@example.com"
        assert added_user.username == "user_name-123"


class TestAuthServiceIntegration:
    """Integration-style tests for auth service"""

    @pytest.mark.asyncio
    async def test_authenticate_then_register_flow(self):
        """Test that authentication fails before registration, succeeds after"""
        # Mock database session
        mock_db = AsyncMock()

        # First attempt: user doesn't exist
        mock_result_not_found = MagicMock()
        mock_result_not_found.scalars().first.return_value = None

        mock_db.execute = AsyncMock(return_value=mock_result_not_found)

        # Authentication should fail
        with pytest.raises(HTTPException):
            await authenticate_user("new@example.com", "password123", mock_db)  # nosec B106

        # Reset mock for registration
        mock_role = Role(id=1, name="user", permissions=[])
        mock_email_check = MagicMock()
        mock_email_check.scalars().first.return_value = None
        mock_role_result = MagicMock()
        mock_role_result.scalars().first.return_value = mock_role

        mock_db.execute = AsyncMock(side_effect=[mock_email_check, mock_role_result])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # Registration should succeed
        await register_user("new@example.com", "newuser", "password123", mock_db)  # nosec B106

        # Verify user was added
        assert mock_db.add.called
