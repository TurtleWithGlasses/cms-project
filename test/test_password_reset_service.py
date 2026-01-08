"""
Tests for Password Reset Service
"""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import hash_password, verify_password
from app.models.password_reset import PasswordResetToken
from app.models.user import Role, User
from app.services.password_reset_service import PasswordResetService


class TestGenerateResetToken:
    """Test reset token generation"""

    def test_generate_token_returns_string(self):
        """Test that token generation returns a string"""
        token = PasswordResetService.generate_reset_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_is_unique(self):
        """Test that generated tokens are unique"""
        tokens = [PasswordResetService.generate_reset_token() for _ in range(100)]
        # All tokens should be unique
        assert len(tokens) == len(set(tokens))

    def test_generate_token_is_urlsafe(self):
        """Test that generated token is URL-safe"""
        token = PasswordResetService.generate_reset_token()
        # URL-safe characters only (alphanumeric, -, _)
        assert all(c.isalnum() or c in "-_" for c in token)


class TestCreateResetToken:
    """Test creating password reset tokens"""

    @pytest.mark.asyncio
    async def test_create_reset_token_for_existing_user(self, test_db: AsyncSession):
        """Test creating reset token for an existing user"""
        # Get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("oldpassword"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create reset token
        reset_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        assert reset_token is not None
        assert reset_token.user_id == user.id
        assert reset_token.token is not None
        assert len(reset_token.token) > 0
        assert reset_token.used is False
        assert reset_token.expires_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_create_reset_token_for_nonexistent_user(self, test_db: AsyncSession):
        """Test that requesting token for non-existent email doesn't reveal if user exists"""
        # This should return 200 OK without revealing if user exists
        # (security best practice to prevent email enumeration)
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.create_reset_token(email="nonexistent@example.com", db=test_db)

        # Should return 200 OK to prevent email enumeration
        assert exc_info.value.status_code == 200

    @pytest.mark.asyncio
    async def test_create_reset_token_invalidates_old_tokens(self, test_db: AsyncSession):
        """Test that creating new token invalidates existing unused tokens"""
        # Get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create first reset token
        first_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Create second reset token (should invalidate first)
        second_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Refresh first token from database
        await test_db.refresh(first_token)

        # First token should be marked as used
        assert first_token.used is True
        # Second token should be valid
        assert second_token.used is False


class TestValidateResetToken:
    """Test validating password reset tokens"""

    @pytest.mark.asyncio
    async def test_validate_valid_token(self, test_db: AsyncSession):
        """Test validating a valid, unexpired, unused token"""
        # Create user and token - get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        reset_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Validate token
        validated_token = await PasswordResetService.validate_reset_token(token=reset_token.token, db=test_db)

        assert validated_token.id == reset_token.id
        assert validated_token.user_id == user.id

    @pytest.mark.asyncio
    async def test_validate_invalid_token(self, test_db: AsyncSession):
        """Test validating a non-existent token raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.validate_reset_token(token="invalid_token_string", db=test_db)

        assert exc_info.value.status_code == 400
        assert "invalid" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_used_token(self, test_db: AsyncSession):
        """Test validating an already-used token raises exception"""
        # Create user and token - get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        reset_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Mark token as used
        reset_token.used = True
        await test_db.commit()

        # Try to validate used token
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.validate_reset_token(token=reset_token.token, db=test_db)

        assert exc_info.value.status_code == 400
        assert "already been used" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_validate_expired_token(self, test_db: AsyncSession):
        """Test validating an expired token raises exception"""
        # Get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create token with past expiry
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=PasswordResetService.generate_reset_token(),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        )
        test_db.add(reset_token)
        await test_db.commit()

        # Try to validate expired token
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.validate_reset_token(token=reset_token.token, db=test_db)

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()


class TestResetPassword:
    """Test password reset functionality"""

    @pytest.mark.asyncio
    async def test_reset_password_successfully(self, test_db: AsyncSession):
        """Test successfully resetting a user's password"""
        # Create user and token - get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        old_password = "oldpassword123"
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password(old_password),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        reset_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Reset password
        new_password = "newpassword456"
        updated_user = await PasswordResetService.reset_password(
            token=reset_token.token, new_password=new_password, db=test_db
        )

        # Verify password was updated
        assert updated_user.id == user.id
        assert verify_password(new_password, updated_user.hashed_password)
        assert not verify_password(old_password, updated_user.hashed_password)

        # Verify token was marked as used
        await test_db.refresh(reset_token)
        assert reset_token.used is True

    @pytest.mark.asyncio
    async def test_reset_password_with_invalid_token(self, test_db: AsyncSession):
        """Test that resetting password with invalid token fails"""
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.reset_password(token="invalid_token", new_password="newpassword", db=test_db)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_reset_password_with_used_token(self, test_db: AsyncSession):
        """Test that using the same token twice fails"""
        # Create user and token - get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        reset_token = await PasswordResetService.create_reset_token(email="testuser@example.com", db=test_db)

        # Use token once
        await PasswordResetService.reset_password(token=reset_token.token, new_password="newpassword1", db=test_db)

        # Try to use the same token again
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.reset_password(token=reset_token.token, new_password="newpassword2", db=test_db)

        assert exc_info.value.status_code == 400
        assert "already been used" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_reset_password_with_expired_token(self, test_db: AsyncSession):
        """Test that resetting password with expired token fails"""
        # Get existing role from fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create expired token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=PasswordResetService.generate_reset_token(),
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        test_db.add(reset_token)
        await test_db.commit()

        # Try to reset password with expired token
        with pytest.raises(HTTPException) as exc_info:
            await PasswordResetService.reset_password(token=reset_token.token, new_password="newpassword", db=test_db)

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()
