"""
Tests for app/auth.py module (password hashing, token management, role validation)
"""

from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth import (
    create_access_token,
    decode_access_token,
    has_permission,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.user import Role, User


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test that password hashing works"""
        password = "Test_Password_123"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 0

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (due to salt)"""
        password = "Test_Password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test verifying a correct password"""
        password = "Test_Password_123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying an incorrect password"""
        password = "Test_Password_123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test verifying empty password"""
        password = "Test_Password_123"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False

    def test_hash_special_characters(self):
        """Test hashing passwords with special characters"""
        passwords = ["p@ssw0rd!", "test#123$456", "unicode_пароль_密码", "emoji_password_🔒"]

        for password in passwords:
            hashed = hash_password(password)
            assert verify_password(password, hashed) is True


class TestCreateAccessToken:
    """Test JWT token creation"""

    def test_create_token_with_sub(self):
        """Test creating token with sub claim"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_without_sub(self):
        """Test that creating token without sub raises ValueError"""
        data = {"email": "test@example.com"}

        with pytest.raises(ValueError) as exc_info:
            create_access_token(data)

        assert "sub" in str(exc_info.value).lower()

    def test_create_token_with_custom_expiry(self):
        """Test creating token with custom expiration"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(hours=24)
        token = create_access_token(data, expires_delta=expires_delta)

        assert token is not None
        # Token should be valid
        email = decode_access_token(token)
        assert email == "test@example.com"

    def test_create_token_with_additional_data(self):
        """Test creating token with additional claims"""
        data = {"sub": "test@example.com", "user_id": 123, "role": "admin"}
        token = create_access_token(data)

        assert token is not None


class TestDecodeAccessToken:
    """Test JWT token decoding"""

    def test_decode_valid_token(self):
        """Test decoding a valid token"""
        data = {"sub": "test@example.com"}
        token = create_access_token(data)

        email = decode_access_token(token)
        assert email == "test@example.com"

    def test_decode_token_without_sub(self):
        """Test decoding token without sub claim raises exception"""
        from jose import jwt

        from app.constants import ALGORITHM, SECRET_KEY

        # Manually create token without 'sub'
        data = {"email": "test@example.com"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401
        assert "sub" in exc_info.value.detail.lower()

    def test_decode_expired_token(self):
        """Test decoding an expired token raises exception"""
        data = {"sub": "test@example.com"}
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(data, expires_delta=expires_delta)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_decode_invalid_token(self):
        """Test decoding an invalid token"""
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_decode_token_with_wrong_secret(self):
        """Test decoding token signed with different secret"""
        from jose import jwt

        data = {"sub": "test@example.com"}
        wrong_token = jwt.encode(data, "wrong_secret_key", algorithm="HS256")

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(wrong_token)

        assert exc_info.value.status_code == 401


@pytest.mark.skip(reason="Database fixture issues - duplicate role creation (see KNOWN_ISSUES.md)")
class TestVerifyToken:
    """Test token verification with database lookup"""

    @pytest.mark.asyncio
    async def test_verify_valid_token_existing_user(self, test_db: AsyncSession):
        """Test verifying a valid token for an existing user"""
        # Create a role and user
        role = Role(name="user", permissions=[])
        test_db.add(role)
        await test_db.commit()
        await test_db.refresh(role)

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("Password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create token
        data = {"sub": user.email}
        token = create_access_token(data)

        # Verify token
        verified_user = await verify_token(token=token, db=test_db)

        assert verified_user is not None
        assert verified_user.email == user.email
        assert verified_user.username == user.username

    @pytest.mark.asyncio
    async def test_verify_token_nonexistent_user(self, test_db: AsyncSession):
        """Test verifying token for non-existent user raises exception"""
        # Create token for user that doesn't exist
        data = {"sub": "nonexistent@example.com"}
        token = create_access_token(data)

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token=token, db=test_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, test_db: AsyncSession):
        """Test verifying an invalid token"""
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token=invalid_token, db=test_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_token_without_sub(self, test_db: AsyncSession):
        """Test verifying token without sub claim"""
        from jose import jwt

        from app.constants import ALGORITHM, SECRET_KEY

        # Create token without 'sub'
        data = {"email": "test@example.com"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(token=token, db=test_db)

        assert exc_info.value.status_code == 401


class TestHasPermission:
    """Test permission validation"""

    def test_admin_wildcard_permission(self):
        """Test that admin with wildcard has all permissions"""
        result = has_permission("admin", "any_permission")
        assert result is True

        result = has_permission("admin", "delete_everything")
        assert result is True

    def test_superadmin_wildcard_permission(self):
        """Test that superadmin with wildcard has all permissions"""
        result = has_permission("superadmin", "critical_operation")
        assert result is True

    def test_specific_permission_granted(self):
        """Test role with specific permission"""
        result = has_permission("editor", "view_content")
        assert result is True

        result = has_permission("editor", "edit_content")
        assert result is True

    def test_specific_permission_denied(self):
        """Test role without specific permission raises exception"""
        with pytest.raises(HTTPException) as exc_info:
            has_permission("user", "delete_content")

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    def test_manager_permissions(self):
        """Test manager role permissions"""
        # Manager should have these permissions
        result = has_permission("manager", "view_content")
        assert result is True

        result = has_permission("manager", "edit_content")
        assert result is True

        result = has_permission("manager", "approve_content")
        assert result is True

    def test_nonexistent_role(self):
        """Test permission check for non-existent role"""
        with pytest.raises(HTTPException) as exc_info:
            has_permission("nonexistent_role", "some_permission")

        assert exc_info.value.status_code == 403

    def test_editor_without_admin_permission(self):
        """Test that editor doesn't have admin-only permissions"""
        # Editor should not have delete permission
        with pytest.raises(HTTPException):
            has_permission("editor", "delete_content")

    def test_user_basic_role(self):
        """Test basic user role has no special permissions"""
        # User role has empty permissions list
        with pytest.raises(HTTPException):
            has_permission("user", "edit_content")

        with pytest.raises(HTTPException):
            has_permission("user", "view_content")


class TestTokenRoundTrip:
    """Test creating, encoding, and decoding tokens"""

    def test_create_decode_roundtrip(self):
        """Test that created token can be decoded"""
        emails = ["user1@example.com", "admin@test.com", "editor@company.org"]

        for email in emails:
            token = create_access_token({"sub": email})
            decoded_email = decode_access_token(token)
            assert decoded_email == email

    @pytest.mark.skip(reason="Non-deterministic test - tokens may have same timestamp (see KNOWN_ISSUES.md)")
    def test_multiple_tokens_same_user(self):
        """Test creating multiple tokens for same user"""
        email = "user@example.com"

        tokens = []
        for _ in range(5):
            token = create_access_token({"sub": email})
            tokens.append(token)

        # All tokens should be valid and decode to same email
        for token in tokens:
            decoded_email = decode_access_token(token)
            assert decoded_email == email

        # Tokens should be different (due to different timestamps)
        assert len(set(tokens)) == 5

    @pytest.mark.skip(reason="Database fixture issues - duplicate role creation (see KNOWN_ISSUES.md)")
    @pytest.mark.asyncio
    async def test_verify_multiple_users(self, test_db: AsyncSession):
        """Test verifying tokens for multiple users"""
        # Create role
        role = Role(name="user", permissions=[])
        test_db.add(role)
        await test_db.commit()
        await test_db.refresh(role)

        # Create multiple users
        users_data = [("user1", "user1@example.com"), ("user2", "user2@example.com"), ("user3", "user3@example.com")]

        for username, email in users_data:
            user = User(username=username, email=email, hashed_password=hash_password("Password123"), role_id=role.id)
            test_db.add(user)

        await test_db.commit()

        # Create and verify tokens for all users
        for username, email in users_data:
            token = create_access_token({"sub": email})
            verified_user = await verify_token(token=token, db=test_db)
            assert verified_user.email == email
            assert verified_user.username == username
