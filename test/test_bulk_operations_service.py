"""
Tests for Bulk Operations Service

Tests bulk operations on content and users for efficiency.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from utils.mock_utils import create_test_category, create_test_content, create_test_tag

from app.models.content import Content, ContentStatus
from app.models.user import Role, User
from app.services.bulk_operations_service import BulkOperationsService, bulk_operations_service


class TestBulkOperationsService:
    """Test bulk operations service functionality"""

    @pytest.fixture
    def bulk_svc(self):
        """Create bulk operations service instance"""
        return BulkOperationsService()

    @pytest.mark.asyncio
    async def test_bulk_publish_content_success(self, async_db_session, test_user):
        """Test bulk publishing pending content"""
        # Create pending content items
        content_ids = []
        for i in range(3):
            content = await create_test_content(
                async_db_session,
                title=f"Pending Post {i}",
                body="Content to publish",
                author_id=test_user.id,
                status=ContentStatus.PENDING,
            )
            content_ids.append(content.id)

        # Bulk publish
        result = await bulk_operations_service.bulk_publish_content(
            content_ids=content_ids,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 3
        assert len(result["success_ids"]) == 3
        assert result["failed_count"] == 0

        # Verify all are published
        for content_id in content_ids:
            result = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result.scalars().first()
            assert content.status == ContentStatus.PUBLISHED

    @pytest.mark.asyncio
    async def test_bulk_publish_content_wrong_status(self, async_db_session, test_user):
        """Test bulk publish only works on pending content"""
        # Create content with different statuses
        draft = await create_test_content(
            async_db_session,
            title="Draft Post",
            body="Draft",
            author_id=test_user.id,
            status=ContentStatus.DRAFT,
        )
        pending = await create_test_content(
            async_db_session,
            title="Pending Post",
            body="Pending",
            author_id=test_user.id,
            status=ContentStatus.PENDING,
        )

        # Try to publish both
        result = await bulk_operations_service.bulk_publish_content(
            content_ids=[draft.id, pending.id],
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 1  # Only pending should succeed
        assert result["failed_count"] == 1
        assert pending.id in result["success_ids"]

    @pytest.mark.asyncio
    async def test_bulk_publish_content_not_found(self, async_db_session, test_user):
        """Test bulk publish handles non-existent IDs"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await bulk_operations_service.bulk_publish_content(
                content_ids=[99999],
                current_user=test_user,
                db=async_db_session,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_bulk_update_content_status(self, async_db_session, test_user):
        """Test bulk updating content status"""
        # Create draft content
        content_ids = []
        for i in range(4):
            content = await create_test_content(
                async_db_session,
                title=f"Draft Post {i}",
                body="Draft content",
                author_id=test_user.id,
                status=ContentStatus.DRAFT,
            )
            content_ids.append(content.id)

        # Update all to pending
        result = await bulk_operations_service.bulk_update_content_status(
            content_ids=content_ids,
            new_status="pending",
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 4
        assert len(result["success_ids"]) == 4

        # Verify status changed
        for content_id in content_ids:
            result_query = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result_query.scalars().first()
            assert content.status == ContentStatus.PENDING

    @pytest.mark.asyncio
    async def test_bulk_update_content_status_invalid(self, async_db_session, test_user):
        """Test bulk update rejects invalid status"""
        from fastapi import HTTPException

        content = await create_test_content(
            async_db_session,
            title="Test Post",
            body="Content",
            author_id=test_user.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await bulk_operations_service.bulk_update_content_status(
                content_ids=[content.id],
                new_status="invalid_status",
                current_user=test_user,
                db=async_db_session,
            )

        assert exc_info.value.status_code == 400
        assert "Invalid status" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bulk_delete_content(self, async_db_session, test_user):
        """Test bulk deleting content"""
        # Create content to delete
        content_ids = []
        for i in range(3):
            content = await create_test_content(
                async_db_session,
                title=f"Delete Post {i}",
                body="To be deleted",
                author_id=test_user.id,
            )
            content_ids.append(content.id)

        # Bulk delete
        result = await bulk_operations_service.bulk_delete_content(
            content_ids=content_ids,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 3
        assert len(result["deleted_ids"]) == 3

        # Verify deleted
        for content_id in content_ids:
            result_query = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result_query.scalars().first()
            assert content is None

    @pytest.mark.asyncio
    async def test_bulk_assign_tags(self, async_db_session, test_user):
        """Test bulk assigning tags to content"""
        # Create content
        content_ids = []
        for i in range(3):
            content = await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=test_user.id,
            )
            content_ids.append(content.id)

        # Create tags
        tag1 = await create_test_tag(async_db_session, name="python")
        tag2 = await create_test_tag(async_db_session, name="tutorial")

        # Bulk assign tags
        result = await bulk_operations_service.bulk_assign_tags(
            content_ids=content_ids,
            tag_ids=[tag1.id, tag2.id],
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 3
        assert result["tags_assigned"] == 2

        # Verify tags assigned
        for content_id in content_ids:
            result_query = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result_query.scalars().first()
            assert len(content.tags) == 2
            tag_names = [tag.name for tag in content.tags]
            assert "python" in tag_names
            assert "tutorial" in tag_names

    @pytest.mark.asyncio
    async def test_bulk_assign_tags_duplicate_prevention(self, async_db_session, test_user):
        """Test bulk assign doesn't create duplicate tags"""
        content = await create_test_content(
            async_db_session,
            title="Post",
            body="Content",
            author_id=test_user.id,
        )
        tag = await create_test_tag(async_db_session, name="existing")

        # Assign tag first time
        content.tags.append(tag)
        await async_db_session.commit()

        # Try to assign same tag again
        result = await bulk_operations_service.bulk_assign_tags(
            content_ids=[content.id],
            tag_ids=[tag.id],
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 1

        # Verify no duplicates
        await async_db_session.refresh(content)
        assert len(content.tags) == 1

    @pytest.mark.asyncio
    async def test_bulk_assign_tags_invalid_tag(self, async_db_session, test_user):
        """Test bulk assign rejects non-existent tags"""
        from fastapi import HTTPException

        content = await create_test_content(
            async_db_session,
            title="Post",
            body="Content",
            author_id=test_user.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await bulk_operations_service.bulk_assign_tags(
                content_ids=[content.id],
                tag_ids=[99999],
                current_user=test_user,
                db=async_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "tags not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bulk_update_category(self, async_db_session, test_user):
        """Test bulk updating content category"""
        # Create category
        category = await create_test_category(async_db_session, name="Tech")

        # Create content
        content_ids = []
        for i in range(3):
            content = await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=test_user.id,
            )
            content_ids.append(content.id)

        # Bulk update category
        result = await bulk_operations_service.bulk_update_category(
            content_ids=content_ids,
            category_id=category.id,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 3
        assert result["new_category"] == "Tech"

        # Verify category updated
        for content_id in content_ids:
            result_query = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result_query.scalars().first()
            assert content.category_id == category.id

    @pytest.mark.asyncio
    async def test_bulk_update_category_invalid(self, async_db_session, test_user):
        """Test bulk category update rejects invalid category"""
        from fastapi import HTTPException

        content = await create_test_content(
            async_db_session,
            title="Post",
            body="Content",
            author_id=test_user.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await bulk_operations_service.bulk_update_category(
                content_ids=[content.id],
                category_id=99999,
                current_user=test_user,
                db=async_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "Category not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles(self, async_db_session, test_user):
        """Test bulk updating user roles"""
        # Get roles
        user_role_result = await async_db_session.execute(select(Role).where(Role.name == "user"))
        user_role = user_role_result.scalars().first()

        editor_role_result = await async_db_session.execute(select(Role).where(Role.name == "editor"))
        editor_role = editor_role_result.scalars().first()

        # Create users with user role
        user_ids = []
        for i in range(3):
            user = User(
                email=f"user{i}@example.com",
                username=f"user{i}",
                hashed_password="hashed",
                role_id=user_role.id,
            )
            async_db_session.add(user)
            await async_db_session.commit()
            await async_db_session.refresh(user)
            user_ids.append(user.id)

        # Bulk update to editor role
        result = await bulk_operations_service.bulk_update_user_roles(
            user_ids=user_ids,
            role_id=editor_role.id,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 3
        assert len(result["success_ids"]) == 3
        assert result["new_role"] == "editor"

        # Verify roles updated
        for user_id in user_ids:
            result_query = await async_db_session.execute(select(User).where(User.id == user_id))
            user = result_query.scalars().first()
            assert user.role_id == editor_role.id

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles_prevent_self(self, async_db_session, test_user):
        """Test cannot change own role via bulk update"""
        editor_role_result = await async_db_session.execute(select(Role).where(Role.name == "editor"))
        editor_role = editor_role_result.scalars().first()

        result = await bulk_operations_service.bulk_update_user_roles(
            user_ids=[test_user.id],
            role_id=editor_role.id,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 0
        assert result["failed_count"] == 1
        assert "Cannot change your own role" in result["failed_items"][0]["reason"]

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles_prevent_superadmin(self, async_db_session, test_user):
        """Test cannot change superadmin roles"""
        # Get superadmin role
        superadmin_role_result = await async_db_session.execute(select(Role).where(Role.name == "superadmin"))
        superadmin_role = superadmin_role_result.scalars().first()

        user_role_result = await async_db_session.execute(select(Role).where(Role.name == "user"))
        user_role = user_role_result.scalars().first()

        # Create superadmin user
        superadmin = User(
            email="superadmin@example.com",
            username="superadmin",
            hashed_password="hashed",
            role_id=superadmin_role.id,
        )
        async_db_session.add(superadmin)
        await async_db_session.commit()
        await async_db_session.refresh(superadmin)

        # Try to change superadmin's role
        result = await bulk_operations_service.bulk_update_user_roles(
            user_ids=[superadmin.id],
            role_id=user_role.id,
            current_user=test_user,
            db=async_db_session,
        )

        assert result["success_count"] == 0
        assert result["failed_count"] == 1
        assert "Cannot change superadmin role" in result["failed_items"][0]["reason"]

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles_invalid_role(self, async_db_session, test_user):
        """Test bulk role update rejects invalid role"""
        from fastapi import HTTPException

        user_role_result = await async_db_session.execute(select(Role).where(Role.name == "user"))
        user_role = user_role_result.scalars().first()

        user = User(
            email="bulkuser@example.com",
            username="bulkuser",
            hashed_password="hashed",
            role_id=user_role.id,
        )
        async_db_session.add(user)
        await async_db_session.commit()
        await async_db_session.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            await bulk_operations_service.bulk_update_user_roles(
                user_ids=[user.id],
                role_id=99999,
                current_user=test_user,
                db=async_db_session,
            )

        assert exc_info.value.status_code == 404
        assert "Role not found" in exc_info.value.detail

    async def test_singleton_instance(self):
        """Test bulk_operations_service singleton exists"""
        assert bulk_operations_service is not None
        assert isinstance(bulk_operations_service, BulkOperationsService)
