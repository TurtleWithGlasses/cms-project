"""
Tests for authentication helper functions (get_current_user, has_permission)
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    get_current_user_from_header as get_current_user,
    has_permission,
    hash_password,
)
from app.models.user import Role, User


class TestGetCurrentUser:
    """Test get_current_user function"""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, test_db: AsyncSession):
        """Test retrieving current user with valid token"""
        from sqlalchemy.future import select

        # Get the existing user role from setup_test_database fixture
        result = await test_db.execute(select(Role).where(Role.name == "user"))
        role = result.scalars().first()

        # Create a user
        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("password123"),
            role_id=role.id,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create token
        token = create_access_token({"sub": user.email})

        # Get current user
        current_user = await get_current_user(token=token, db=test_db)

        assert current_user is not None
        assert current_user.email == "testuser@example.com"
        assert current_user.username == "testuser"
        assert current_user.role.name == "user"

    @pytest.mark.asyncio
    async def test_get_current_user_with_invalid_token(self, test_db: AsyncSession):
        """Test that invalid token raises HTTPException"""
        invalid_token = "invalid.token.string"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=invalid_token, db=test_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_with_nonexistent_email(self, test_db: AsyncSession):
        """Test that token with non-existent email raises 404"""
        # Create token for user that doesn't exist
        token = create_access_token({"sub": "nonexistent@example.com"})

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.skip(reason="Database constraint prevents users without roles (role_id is NOT NULL)")
    @pytest.mark.asyncio
    async def test_get_current_user_without_role(self, test_db: AsyncSession):
        """Test that user without role raises 403"""
        # Note: This scenario is prevented by database constraints (role_id is NOT NULL)
        # The auth code has defensive checks for this, but it can't actually happen
        # Create user without a valid role
        user = User(
            username="noroleuser",
            email="norole@example.com",
            hashed_password=hash_password("password123"),
            role_id=None,  # No role assigned
        )
        test_db.add(user)
        await test_db.commit()

        token = create_access_token({"sub": user.email})

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)

        assert exc_info.value.status_code == 403
        assert "role" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_with_expired_token(self, test_db: AsyncSession):
        """Test that expired token raises 401"""
        from datetime import timedelta

        from sqlalchemy.future import select

        # Get the existing user role from setup_test_database fixture
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

        # Create already-expired token
        token = create_access_token({"sub": user.email}, expires_delta=timedelta(seconds=-1))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=test_db)

        assert exc_info.value.status_code == 401
        # get_current_user_from_header normalizes all auth errors to generic message for security
        assert "could not validate credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_current_user_with_different_roles(self, test_db: AsyncSession):
        """Test retrieving users with different roles"""
        from sqlalchemy.future import select

        # Use existing roles from setup_test_database fixture
        # Create users with different roles
        users_data = [
            ("user1", "user1@example.com", "user"),
            ("admin1", "admin1@example.com", "admin"),
            ("editor1", "editor1@example.com", "editor"),
        ]

        for username, email, role_name in users_data:
            # Find existing role
            result = await test_db.execute(select(Role).where(Role.name == role_name))
            role = result.scalars().first()

            user = User(username=username, email=email, hashed_password=hash_password("password123"), role_id=role.id)
            test_db.add(user)

        await test_db.commit()

        # Test each user
        for username, email, expected_role in users_data:
            token = create_access_token({"sub": email})
            current_user = await get_current_user(token=token, db=test_db)

            assert current_user.email == email
            assert current_user.username == username
            assert current_user.role.name == expected_role


class TestHasPermission:
    """Test has_permission function"""

    def test_admin_has_all_permissions(self):
        """Test that admin role with '*' has all permissions"""
        # Admin role has wildcard permission
        result = has_permission("admin", "any_permission")
        assert result is True

        result = has_permission("admin", "delete_users")
        assert result is True

    def test_superadmin_has_all_permissions(self):
        """Test that superadmin role has all permissions"""
        result = has_permission("superadmin", "critical_operation")
        assert result is True

    def test_user_with_specific_permission(self):
        """Test role with specific permission"""
        # Editor has view_content and edit_content permissions
        result = has_permission("editor", "view_content")
        assert result is True

        result = has_permission("editor", "edit_content")
        assert result is True

    def test_manager_has_approve_permission(self):
        """Test manager role has approve_content permission"""
        result = has_permission("manager", "view_content")
        assert result is True

        result = has_permission("manager", "edit_content")
        assert result is True

        result = has_permission("manager", "approve_content")
        assert result is True

    def test_user_without_permission_raises_exception(self):
        """Test that user without permission raises HTTPException"""
        # Regular user doesn't have admin permissions
        with pytest.raises(HTTPException) as exc_info:
            has_permission("user", "delete_users")

        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()

    def test_editor_without_admin_permission(self):
        """Test that editor doesn't have admin-only permissions"""
        # Editor doesn't have delete permission
        with pytest.raises(HTTPException) as exc_info:
            has_permission("editor", "delete_content")

        assert exc_info.value.status_code == 403

    def test_nonexistent_role(self):
        """Test checking permissions for non-existent role"""
        with pytest.raises(HTTPException) as exc_info:
            has_permission("nonexistent_role", "some_permission")

        assert exc_info.value.status_code == 403

    def test_permission_check_case_sensitivity(self):
        """Test that permission checks are case-sensitive"""
        # Exact permission match required
        result = has_permission("editor", "view_content")
        assert result is True

        # Different case should fail
        with pytest.raises(HTTPException):
            has_permission("editor", "VIEW_CONTENT")

    def test_multiple_permission_checks_for_same_role(self):
        """Test multiple permission checks for the same role"""
        # Manager has multiple permissions
        permissions_to_check = ["view_content", "edit_content", "approve_content"]

        for permission in permissions_to_check:
            result = has_permission("manager", permission)
            assert result is True

        # Manager doesn't have delete permission
        with pytest.raises(HTTPException):
            has_permission("manager", "delete_content")
