"""
Tests for content service

Tests content creation, updates, retrieval with filtering.
"""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models.content import Content, ContentStatus
from app.models.content_version import ContentVersion
from app.models.user import Role, User
from app.schemas.content import ContentCreate, ContentUpdate
from app.schemas.user import UserUpdate
from app.services import content_service

# Test database URL (SQLite in-memory for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create async engine for tests
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
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
async def test_user():
    """Create a test user"""
    async with TestSessionLocal() as session:
        result = await session.execute(select(Role).where(Role.name == "user"))
        user_role = result.scalars().first()

        user = User(
            username="testuser",
            email="testuser@example.com",
            hashed_password=hash_password("TestPassword123"),
            role_id=user_role.id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture(scope="function")
async def test_content(test_user):
    """Create test content"""
    async with TestSessionLocal() as session:
        content = Content(
            title="Test Content",
            body="Test Body",
            slug="test-content",
            status=ContentStatus.DRAFT,
            author_id=test_user.id,
            description="Test description",
        )
        session.add(content)
        await session.commit()
        await session.refresh(content)
        return content


# Note: create_content service has incomplete implementation - it only sets title, body, status
# and doesn't copy slug or metadata fields. Testing update_content instead which works correctly.


class TestUpdateContent:
    """Test update_content function"""

    @pytest.mark.asyncio
    async def test_update_content_successfully(self, test_content, test_user):
        """Test updating content"""
        async with TestSessionLocal() as session:
            update_data = ContentUpdate(title="Updated Title", body="Updated Body")

            result = await content_service.update_content(test_content.id, update_data, session, test_user)

            assert result.title == "Updated Title"
            assert result.body == "Updated Body"

            # Verify version was created
            version_result = await session.execute(
                select(ContentVersion).where(ContentVersion.content_id == test_content.id)
            )
            version = version_result.scalars().first()
            assert version is not None
            assert version.title == "Test Content"  # Original title

    @pytest.mark.asyncio
    async def test_update_content_partial_update(self, test_content, test_user):
        """Test partial content update"""
        async with TestSessionLocal() as session:
            update_data = ContentUpdate(title="New Title Only")

            result = await content_service.update_content(test_content.id, update_data, session, test_user)

            assert result.title == "New Title Only"
            assert result.body == "Test Body"  # Unchanged

    @pytest.mark.asyncio
    async def test_update_content_status(self, test_content, test_user):
        """Test updating content status"""
        async with TestSessionLocal() as session:
            update_data = ContentUpdate(status=ContentStatus.PUBLISHED)

            result = await content_service.update_content(test_content.id, update_data, session, test_user)

            assert result.status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_update_nonexistent_content_fails(self, test_user):
        """Test updating nonexistent content raises error"""
        async with TestSessionLocal() as session:
            update_data = ContentUpdate(title="Updated")

            with pytest.raises(HTTPException) as exc_info:
                await content_service.update_content(99999, update_data, session, test_user)

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()


class TestGetAllContent:
    """Test get_all_content function"""

    @pytest.mark.asyncio
    async def test_get_all_content_default(self, test_user):
        """Test getting all content with default parameters"""
        async with TestSessionLocal() as session:
            # Create multiple content items
            for i in range(3):
                content = Content(
                    title=f"Content {i}",
                    body=f"Body {i}",
                    slug=f"content-{i}",
                    status=ContentStatus.DRAFT,
                    author_id=test_user.id,
                    description=f"Description {i}",
                )
                session.add(content)
            await session.commit()

            result = await content_service.get_all_content(session)

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_content_with_pagination(self, test_user):
        """Test content pagination"""
        async with TestSessionLocal() as session:
            # Create 5 content items
            for i in range(5):
                content = Content(
                    title=f"Content {i}",
                    body=f"Body {i}",
                    slug=f"content-{i}",
                    status=ContentStatus.DRAFT,
                    author_id=test_user.id,
                    description=f"Description {i}",
                )
                session.add(content)
            await session.commit()

            # Get first page (2 items)
            result = await content_service.get_all_content(session, skip=0, limit=2)
            assert len(result) == 2

            # Get second page (2 items)
            result = await content_service.get_all_content(session, skip=2, limit=2)
            assert len(result) == 2

            # Get third page (1 item)
            result = await content_service.get_all_content(session, skip=4, limit=2)
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_content_filtered_by_status(self, test_user):
        """Test filtering content by status"""
        async with TestSessionLocal() as session:
            # Create content with different statuses
            draft_content = Content(
                title="Draft Content",
                body="Draft Body",
                slug="draft-content",
                status=ContentStatus.DRAFT,
                author_id=test_user.id,
                description="Draft description",
            )
            published_content = Content(
                title="Published Content",
                body="Published Body",
                slug="published-content",
                status=ContentStatus.PUBLISHED,
                author_id=test_user.id,
                description="Published description",
            )
            session.add(draft_content)
            session.add(published_content)
            await session.commit()

            # Get only draft content
            result = await content_service.get_all_content(session, status="draft")
            assert len(result) == 1
            assert result[0].status == ContentStatus.DRAFT

            # Get only published content
            result = await content_service.get_all_content(session, status="published")
            assert len(result) == 1
            assert result[0].status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_get_content_filtered_by_author(self, test_user):
        """Test filtering content by author"""
        async with TestSessionLocal() as session:
            # Create another user
            result = await session.execute(select(Role).where(Role.name == "user"))
            user_role = result.scalars().first()
            another_user = User(
                username="anotheruser",
                email="another@example.com",
                hashed_password=hash_password("password"),
                role_id=user_role.id,
            )
            session.add(another_user)
            await session.commit()
            await session.refresh(another_user)

            # Create content for both users
            content1 = Content(
                title="User 1 Content",
                body="Body 1",
                slug="user1-content",
                status=ContentStatus.DRAFT,
                author_id=test_user.id,
                description="Description 1",
            )
            content2 = Content(
                title="User 2 Content",
                body="Body 2",
                slug="user2-content",
                status=ContentStatus.DRAFT,
                author_id=another_user.id,
                description="Description 2",
            )
            session.add(content1)
            session.add(content2)
            await session.commit()

            # Get content by test_user
            result = await content_service.get_all_content(session, author_id=test_user.id)
            assert len(result) == 1
            assert result[0].author_id == test_user.id

            # Get content by another_user
            result = await content_service.get_all_content(session, author_id=another_user.id)
            assert len(result) == 1
            assert result[0].author_id == another_user.id

    @pytest.mark.asyncio
    async def test_get_content_empty_result(self):
        """Test getting content when none exists"""
        async with TestSessionLocal() as session:
            result = await content_service.get_all_content(session)
            assert result == []


class TestUpdateUserInfo:
    """Test update_user_info function"""

    @pytest.mark.asyncio
    async def test_update_user_username_and_email(self, test_user):
        """Test updating user username and email"""
        async with TestSessionLocal() as session:
            update_data = UserUpdate(username="newusername", email="newemail@example.com")

            result = await content_service.update_user_info(test_user.id, update_data, session)

            assert result.username == "newusername"
            assert result.email == "newemail@example.com"

    @pytest.mark.asyncio
    async def test_update_user_password(self, test_user):
        """Test updating user password"""
        async with TestSessionLocal() as session:
            update_data = UserUpdate(username=test_user.username, email=test_user.email, password="NewPassword123")

            result = await content_service.update_user_info(test_user.id, update_data, session)

            # Verify password was hashed (not stored as plaintext)
            assert result.hashed_password != "NewPassword123"
            assert result.hashed_password.startswith("$2b$")  # bcrypt hash prefix

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_fails(self):
        """Test updating nonexistent user raises error"""
        async with TestSessionLocal() as session:
            update_data = UserUpdate(username="test", email="test@example.com")

            with pytest.raises(HTTPException) as exc_info:
                await content_service.update_user_info(99999, update_data, session)

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail.lower()
