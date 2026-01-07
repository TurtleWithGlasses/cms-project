"""
Tests for content version service

Tests content versioning functionality including creation, retrieval, and rollback.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from app.auth import hash_password
from app.database import Base
from app.models.content import Content, ContentStatus
from app.models.content_version import ContentVersion
from app.models.user import Role, User
from app.services import content_version_service

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
            hashed_password=hash_password("testpassword"),
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
            title="Original Title",
            body="Original Body",
            slug="original-title",
            status=ContentStatus.DRAFT,
            author_id=test_user.id,
            description="Test description",
        )
        session.add(content)
        await session.commit()
        await session.refresh(content)
        return content


class TestCreateVersionFromContent:
    """Test create_version_from_content function"""

    @pytest.mark.asyncio
    async def test_create_version_successfully(self, test_content, test_user):
        """Test creating a version from content"""
        async with TestSessionLocal() as session:
            # Create version
            await content_version_service.create_version_from_content(test_content, session, test_user)

            # Verify version was created
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            version = result.scalars().first()

            assert version is not None
            assert version.content_id == test_content.id
            assert version.title == test_content.title
            assert version.body == test_content.body
            assert version.slug == test_content.slug
            assert version.status == test_content.status
            assert version.author_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_version_with_metadata(self, test_user):
        """Test creating version with metadata fields"""
        async with TestSessionLocal() as session:
            # Create content with metadata
            content = Content(
                title="Test Title",
                body="Test Body",
                slug="test-title",
                status=ContentStatus.DRAFT,
                author_id=test_user.id,
                meta_title="Meta Title",
                meta_description="Meta Description",
                meta_keywords="keyword1, keyword2",
                description="Test description",
            )
            session.add(content)
            await session.commit()
            await session.refresh(content)

            # Create version
            await content_version_service.create_version_from_content(content, session, test_user)

            # Verify metadata was saved
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == content.id))
            version = result.scalars().first()

            assert version.meta_title == "Meta Title"
            assert version.meta_description == "Meta Description"
            assert version.meta_keywords == "keyword1, keyword2"

    @pytest.mark.asyncio
    async def test_create_multiple_versions(self, test_content, test_user):
        """Test creating multiple versions for same content"""
        async with TestSessionLocal() as session:
            # Create first version
            await content_version_service.create_version_from_content(test_content, session, test_user)

            # Create second version
            await content_version_service.create_version_from_content(test_content, session, test_user)

            # Verify both versions exist
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            versions = result.scalars().all()

            assert len(versions) == 2


class TestGetVersions:
    """Test get_versions function"""

    @pytest.mark.asyncio
    async def test_get_versions_for_content(self, test_content, test_user):
        """Test getting all versions for a content"""
        async with TestSessionLocal() as session:
            # Create multiple versions
            for _ in range(3):
                await content_version_service.create_version_from_content(test_content, session, test_user)

            # Get versions
            versions = await content_version_service.get_versions(test_content.id, session)

            assert len(versions) == 3
            # Verify they're ordered by created_at descending (newest first)
            assert versions[0].created_at >= versions[1].created_at >= versions[2].created_at

    @pytest.mark.asyncio
    async def test_get_versions_empty_list(self, test_content):
        """Test getting versions when none exist"""
        async with TestSessionLocal() as session:
            versions = await content_version_service.get_versions(test_content.id, session)

            assert versions == []

    @pytest.mark.asyncio
    async def test_get_versions_for_nonexistent_content(self):
        """Test getting versions for nonexistent content returns empty list"""
        async with TestSessionLocal() as session:
            versions = await content_version_service.get_versions(99999, session)

            assert versions == []


class TestRollbackToVersion:
    """Test rollback_to_version function"""

    @pytest.mark.asyncio
    async def test_rollback_to_version_successfully(self, test_content, test_user):
        """Test rolling back content to a previous version"""
        async with TestSessionLocal() as session:
            # Create initial version
            await content_version_service.create_version_from_content(test_content, session, test_user)

            # Modify content
            result = await session.execute(select(Content).where(Content.id == test_content.id))
            content = result.scalars().first()
            content.title = "Modified Title"
            content.body = "Modified Body"
            await session.commit()

            # Get the original version
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            original_version = result.scalars().first()

            # Rollback to original version
            rolled_back = await content_version_service.rollback_to_version(
                test_content.id, original_version.id, session, test_user
            )

            assert rolled_back.title == "Original Title"
            assert rolled_back.body == "Original Body"

    @pytest.mark.asyncio
    async def test_rollback_creates_backup_version(self, test_content, test_user):
        """Test that rollback creates a backup version before rolling back"""
        async with TestSessionLocal() as session:
            # Create initial version
            await content_version_service.create_version_from_content(test_content, session, test_user)

            # Modify content
            result = await session.execute(select(Content).where(Content.id == test_content.id))
            content = result.scalars().first()
            content.title = "Modified Title"
            await session.commit()

            # Get the original version
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            original_version = result.scalars().first()

            # Count versions before rollback
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            versions_before = len(result.scalars().all())

            # Rollback
            await content_version_service.rollback_to_version(test_content.id, original_version.id, session, test_user)

            # Count versions after rollback
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == test_content.id))
            versions_after = len(result.scalars().all())

            # Should have one more version (the backup before rollback)
            assert versions_after == versions_before + 1

    @pytest.mark.asyncio
    async def test_rollback_to_nonexistent_version_fails(self, test_content, test_user):
        """Test rollback to nonexistent version raises error"""
        from fastapi import HTTPException

        async with TestSessionLocal() as session:
            with pytest.raises(HTTPException) as exc_info:
                await content_version_service.rollback_to_version(test_content.id, 99999, session, test_user)

            assert exc_info.value.status_code == 404
            assert "version not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rollback_to_version_of_different_content_fails(self, test_content, test_user):
        """Test rollback fails when version belongs to different content"""
        async with TestSessionLocal() as session:
            from fastapi import HTTPException

            # Create another content and version
            other_content = Content(
                title="Other Content",
                body="Other Body",
                slug="other-content",
                status=ContentStatus.DRAFT,
                author_id=test_user.id,
                description="Other description",
            )
            session.add(other_content)
            await session.commit()
            await session.refresh(other_content)

            await content_version_service.create_version_from_content(other_content, session, test_user)

            # Get the other content's version
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == other_content.id))
            other_version = result.scalars().first()

            # Try to rollback test_content to other_content's version
            with pytest.raises(HTTPException) as exc_info:
                await content_version_service.rollback_to_version(test_content.id, other_version.id, session, test_user)

            assert exc_info.value.status_code == 404
            assert "version not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rollback_with_metadata(self, test_user):
        """Test rollback preserves metadata fields"""
        async with TestSessionLocal() as session:
            # Create content with metadata
            content = Content(
                title="Original Title",
                body="Original Body",
                slug="original-slug",
                status=ContentStatus.DRAFT,
                author_id=test_user.id,
                meta_title="Original Meta",
                meta_description="Original Description",
                meta_keywords="original, keywords",
                description="Test description",
            )
            session.add(content)
            await session.commit()
            await session.refresh(content)

            # Create version
            await content_version_service.create_version_from_content(content, session, test_user)

            # Modify content
            result = await session.execute(select(Content).where(Content.id == content.id))
            content_obj = result.scalars().first()
            content_obj.meta_title = "Modified Meta"
            content_obj.meta_description = "Modified Description"
            await session.commit()

            # Get original version
            result = await session.execute(select(ContentVersion).where(ContentVersion.content_id == content.id))
            original_version = result.scalars().first()

            # Rollback
            rolled_back = await content_version_service.rollback_to_version(
                content.id, original_version.id, session, test_user
            )

            assert rolled_back.meta_title == "Original Meta"
            assert rolled_back.meta_description == "Original Description"
            assert rolled_back.meta_keywords == "original, keywords"
