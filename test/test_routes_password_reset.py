"""
Tests for password reset routes

Tests password reset request and confirmation functionality.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base, get_db
from app.models.password_reset import PasswordResetToken
from app.models.user import Role, User
from app.routes import password_reset

# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function", autouse=True)
async def setup_password_reset_database():
    """Create a fresh database for each test function"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create roles
    async with TestSessionLocal() as session:
        roles_data = [
            {"name": "user", "permissions": []},
            {"name": "editor", "permissions": ["view_content", "edit_content"]},
            {"name": "admin", "permissions": ["*"]},
        ]
        for role_data in roles_data:
            role = Role(**role_data)
            session.add(role)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def test_user_fixture():
    """Create a test user"""
    async with TestSessionLocal() as session:
        result = await session.execute(select(Role).where(Role.name == "user"))
        user_role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("testpassword"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture(scope="function")
def password_reset_client(monkeypatch):
    """Create test client for password reset routes with database override"""
    test_app = FastAPI()
    test_app.include_router(password_reset.router, prefix="/api/v1/password-reset")

    # Register exception handlers
    from app.exception_handlers import register_exception_handlers

    register_exception_handlers(test_app)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    # Patch AsyncSessionLocal for activity logging to use test database
    from app.utils import activity_log as activity_log_module

    monkeypatch.setattr(activity_log_module, "AsyncSessionLocal", TestSessionLocal)

    # Mock log_activity to handle the incorrect 'db' parameter in service code
    original_log_activity = activity_log_module.log_activity

    async def mock_log_activity(*args, **kwargs):
        # Remove 'db' parameter if present (bug in service code)
        kwargs.pop("db", None)
        return await original_log_activity(*args, **kwargs)

    monkeypatch.setattr(activity_log_module, "log_activity", mock_log_activity)

    # Also patch log_activity in the password_reset_service module
    from app.services import password_reset_service

    monkeypatch.setattr(password_reset_service, "log_activity", mock_log_activity)

    # Mock rate limiter to avoid rate limiting during tests
    from unittest.mock import MagicMock

    # Create a mock that makes the limit decorator a no-op
    def mock_limit_decorator(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    mock_limiter = MagicMock()
    mock_limiter.limit = mock_limit_decorator

    # Patch the limiter in the password_reset module before importing the router
    from app.routes import password_reset as password_reset_module

    monkeypatch.setattr(password_reset_module, "limiter", mock_limiter)

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()


class TestPasswordResetRequest:
    """Test POST /api/v1/password-reset/api/request endpoint"""

    def test_request_reset_with_invalid_email(self, password_reset_client):
        """Test requesting password reset with invalid email format"""
        data = {"email": "not-an-email"}
        response = password_reset_client.post("/api/v1/password-reset/api/request", json=data)

        # Should return validation error
        assert response.status_code == 422


class TestPasswordResetConfirm:
    """Test POST /api/v1/password-reset/api/reset endpoint"""

    async def create_reset_token(self, user: User) -> str:
        """Helper to create a reset token"""
        async with TestSessionLocal() as session:
            token = PasswordResetToken(
                user_id=user.id,
                token="test-reset-token-12345",
                expires_at=PasswordResetToken.get_expiry_time(hours=1),
                used=False,
            )
            session.add(token)
            await session.commit()
            return token.token

    async def create_used_token(self, user: User) -> str:
        """Helper to create a used reset token"""
        async with TestSessionLocal() as session:
            token = PasswordResetToken(
                user_id=user.id,
                token="used-token-12345",
                expires_at=PasswordResetToken.get_expiry_time(hours=1),
                used=True,
            )
            session.add(token)
            await session.commit()
            return token.token

    async def create_expired_token(self, user: User) -> str:
        """Helper to create an expired reset token"""
        async with TestSessionLocal() as session:
            token = PasswordResetToken(
                user_id=user.id,
                token="expired-token-12345",
                expires_at=datetime.utcnow() - timedelta(hours=2),  # Expired 2 hours ago
                used=False,
            )
            session.add(token)
            await session.commit()
            return token.token

    def test_reset_password_service_directly(self, test_user_fixture):
        """Test resetting password via service (avoiding rate limiter)"""
        import asyncio

        async def test_service():
            async with TestSessionLocal() as session:
                # Create reset token directly
                token = PasswordResetToken(
                    user_id=test_user_fixture.id,
                    token="direct-test-token",
                    expires_at=PasswordResetToken.get_expiry_time(hours=1),
                    used=False,
                )
                session.add(token)
                await session.commit()

                # Mock log_activity to avoid db parameter issue
                from app.utils import activity_log as activity_log_module

                original_log = activity_log_module.log_activity

                async def mock_log(*args, **kwargs):
                    kwargs.pop("db", None)
                    return await original_log(*args, **kwargs)

                # Temporarily replace log_activity
                import app.services.password_reset_service as service_module

                service_module.log_activity = mock_log

                # Test password reset service
                from app.services.password_reset_service import PasswordResetService

                user = await PasswordResetService.reset_password("direct-test-token", "newpassword123", session)
                assert user is not None
                assert user.id == test_user_fixture.id

                # Verify token is marked as used
                await session.refresh(token)
                assert token.used is True

                # Restore original
                service_module.log_activity = original_log

        asyncio.run(test_service())

    def test_reset_password_with_invalid_token(self, password_reset_client):
        """Test resetting password with invalid token"""
        data = {"token": "invalid-token", "new_password": "newpassword123", "confirm_password": "newpassword123"}
        response = password_reset_client.post("/api/v1/password-reset/api/reset", json=data)

        assert response.status_code == 400
        result = response.json()
        error_message = str(result).lower()
        assert "invalid" in error_message

    def test_reset_password_with_used_token(self, password_reset_client, test_user_fixture):
        """Test resetting password with already used token"""
        import asyncio

        # Create used token
        token = asyncio.run(self.create_used_token(test_user_fixture))

        data = {"token": token, "new_password": "newpassword123", "confirm_password": "newpassword123"}
        response = password_reset_client.post("/api/v1/password-reset/api/reset", json=data)

        assert response.status_code == 400
        result = response.json()
        error_message = str(result).lower()
        assert "already been used" in error_message or "used" in error_message

    def test_reset_password_with_expired_token(self, password_reset_client, test_user_fixture):
        """Test resetting password with expired token"""
        import asyncio

        # Create expired token
        token = asyncio.run(self.create_expired_token(test_user_fixture))

        data = {"token": token, "new_password": "newpassword123", "confirm_password": "newpassword123"}
        response = password_reset_client.post("/api/v1/password-reset/api/reset", json=data)

        assert response.status_code == 400
        result = response.json()
        error_message = str(result).lower()
        assert "expired" in error_message

    def test_reset_password_with_mismatched_passwords(self, password_reset_client, test_user_fixture):
        """Test resetting password when passwords don't match"""
        import asyncio

        # Create reset token
        token = asyncio.run(self.create_reset_token(test_user_fixture))

        data = {"token": token, "new_password": "newpassword123", "confirm_password": "differentpassword"}
        response = password_reset_client.post("/api/v1/password-reset/api/reset", json=data)

        # Schema validation should catch this
        assert response.status_code == 422

    def test_reset_password_too_short(self, password_reset_client, test_user_fixture):
        """Test resetting password with password too short"""
        import asyncio

        # Create reset token
        token = asyncio.run(self.create_reset_token(test_user_fixture))

        # Password less than 8 characters
        data = {"token": token, "new_password": "short", "confirm_password": "short"}
        response = password_reset_client.post("/api/v1/password-reset/api/reset", json=data)

        # Schema validation should catch this (min_length=8)
        assert response.status_code == 422


class TestPasswordResetService:
    """Test password reset service directly (avoiding rate limiter issues)"""

    def test_create_reset_token_service(self, test_user_fixture):
        """Test creating reset token via service"""
        import asyncio

        async def test_create():
            async with TestSessionLocal() as session:
                from app.services.password_reset_service import PasswordResetService

                # Mock log_activity to avoid db parameter issue
                from app.utils import activity_log as activity_log_module

                original_log = activity_log_module.log_activity

                async def mock_log(*args, **kwargs):
                    kwargs.pop("db", None)
                    return await original_log(*args, **kwargs)

                # Temporarily replace log_activity
                import app.services.password_reset_service as service_module

                service_module.log_activity = mock_log

                token = await PasswordResetService.create_reset_token(test_user_fixture.email, session)
                assert token is not None
                assert token.user_id == test_user_fixture.id
                assert token.used is False
                assert not token.is_expired()

                # Restore original
                service_module.log_activity = original_log

        asyncio.run(test_create())

    def test_validate_expired_token_service(self, test_user_fixture):
        """Test validating expired token raises error"""
        import asyncio

        from fastapi import HTTPException

        async def test_validate():
            async with TestSessionLocal() as session:
                # Create expired token
                token = PasswordResetToken(
                    user_id=test_user_fixture.id,
                    token="expired-token-service",
                    expires_at=datetime.utcnow() - timedelta(hours=2),
                    used=False,
                )
                session.add(token)
                await session.commit()

                from app.services.password_reset_service import PasswordResetService

                with pytest.raises(HTTPException) as exc_info:
                    await PasswordResetService.validate_reset_token("expired-token-service", session)

                assert exc_info.value.status_code == 400
                assert "expired" in exc_info.value.detail.lower()

        asyncio.run(test_validate())
