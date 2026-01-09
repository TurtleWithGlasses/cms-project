"""
Tests for roles routes

Covers all endpoints in app/routes/roles.py
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.models.user import Role
from app.routes import roles

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Create fresh database for each test"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create test roles
    async with TestSessionLocal() as session:
        test_roles = [
            Role(name="user", permissions=[]),
            Role(name="editor", permissions=["view_content", "edit_content"]),
            Role(name="admin", permissions=["*"]),
            Role(name="superadmin", permissions=["*"]),
        ]
        for role in test_roles:
            session.add(role)
        await session.commit()

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def roles_client():
    """Create test client with dependency overrides"""
    test_app = FastAPI()
    test_app.include_router(roles.router, prefix="/api/v1/roles")

    from app.exception_handlers import register_exception_handlers

    register_exception_handlers(test_app)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    test_app.dependency_overrides[get_db] = override_get_db

    with TestClient(test_app) as client:
        yield client
    test_app.dependency_overrides.clear()


class TestGetRoles:
    """Test GET /roles endpoint"""

    def test_get_all_roles_success(self, roles_client):
        """Test fetching all roles successfully"""
        response = roles_client.get("/api/v1/roles/")

        assert response.status_code == 200
        roles_list = response.json()

        # Should return list of role names
        assert isinstance(roles_list, list)
        assert len(roles_list) == 4
        assert "user" in roles_list
        assert "editor" in roles_list
        assert "admin" in roles_list
        assert "superadmin" in roles_list

    def test_get_roles_returns_strings(self, roles_client):
        """Test that roles endpoint returns list of strings"""
        response = roles_client.get("/api/v1/roles/")

        assert response.status_code == 200
        roles_list = response.json()

        # All items should be strings
        for role in roles_list:
            assert isinstance(role, str)

    def test_get_roles_no_duplicates(self, roles_client):
        """Test that roles list has no duplicates"""
        response = roles_client.get("/api/v1/roles/")

        assert response.status_code == 200
        roles_list = response.json()

        # No duplicates
        assert len(roles_list) == len(set(roles_list))


class TestRolesIntegration:
    """Integration tests for roles"""

    def test_roles_endpoint_accessible_without_auth(self, roles_client):
        """Test that roles endpoint doesn't require authentication"""
        # No auth headers provided
        response = roles_client.get("/api/v1/roles/")

        # Should still work
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_roles_list_is_consistent(self, roles_client):
        """Test that roles list is consistent across multiple calls"""
        response1 = roles_client.get("/api/v1/roles/")
        response2 = roles_client.get("/api/v1/roles/")

        assert response1.json() == response2.json()
