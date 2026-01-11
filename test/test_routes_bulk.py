"""
Tests for Bulk Operations Routes

Tests API endpoints for bulk operations on content and users.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from utils.mock_utils import create_test_category, create_test_content, create_test_tag

from app.models.content import Content, ContentStatus
from app.models.user import Role, User


class TestBulkOperationsRoutes:
    """Test bulk operations API endpoints"""

    @pytest.mark.asyncio
    async def test_bulk_publish_content_success(self, client, async_db_session, admin_user, mock_current_user_storage):
        """Test bulk publishing content as admin"""
        # Set the authenticated user for this test
        mock_current_user_storage["user"] = admin_user

        # Create pending content
        content_ids = []
        for i in range(3):
            content = await create_test_content(
                async_db_session,
                title=f"Pending {i}",
                body="Content",
                author_id=admin_user.id,
                status=ContentStatus.PENDING,
            )
            content_ids.append(content.id)

        response = client.post(
            "/api/v1/bulk/content/publish",
            json={"content_ids": content_ids},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
        assert len(data["success_ids"]) == 3
        assert "Published 3 content items" in data["message"]

    @pytest.mark.asyncio
    async def test_bulk_publish_content_unauthorized(self, client, auth_headers):
        """Test bulk publish requires admin/manager role"""
        response = client.post(
            "/api/v1/bulk/content/publish",
            json={"content_ids": [1, 2, 3]},
            headers=auth_headers,  # Regular user
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_update_content_status(self, client, async_db_session, admin_user):
        """Test bulk updating content status"""
        from app.auth import create_access_token

        # Create draft content
        content_ids = []
        for i in range(2):
            content = await create_test_content(
                async_db_session,
                title=f"Draft {i}",
                body="Content",
                author_id=admin_user.id,
                status=ContentStatus.DRAFT,
            )
            content_ids.append(content.id)

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/update-status",
            json={"content_ids": content_ids, "status": "pending"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert "Updated status for 2 content items to pending" in data["message"]

    @pytest.mark.asyncio
    async def test_bulk_update_content_status_invalid(self, client, admin_user):
        """Test bulk update rejects invalid status"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/update-status",
            json={"content_ids": [1], "status": "invalid"},
            headers=headers,
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_delete_content(self, client, async_db_session, admin_user):
        """Test bulk deleting content"""
        from app.auth import create_access_token

        # Create content to delete
        content_ids = []
        for i in range(2):
            content = await create_test_content(
                async_db_session,
                title=f"Delete {i}",
                body="Content",
                author_id=admin_user.id,
            )
            content_ids.append(content.id)

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/delete",
            json={"content_ids": content_ids},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert "Deleted 2 content items" in data["message"]

        # Verify deleted
        for content_id in content_ids:
            result = await async_db_session.execute(select(Content).where(Content.id == content_id))
            assert result.scalars().first() is None

    @pytest.mark.asyncio
    async def test_bulk_delete_content_requires_admin(self, client, editor_user):
        """Test bulk delete requires admin role (not editor)"""
        from app.auth import create_access_token

        editor_token = create_access_token({"sub": editor_user.email})
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = client.post(
            "/api/v1/bulk/content/delete",
            json={"content_ids": [1, 2]},
            headers=headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_assign_tags(self, client, async_db_session, editor_user):
        """Test bulk assigning tags to content"""
        from app.auth import create_access_token

        # Create content
        content = await create_test_content(
            async_db_session,
            title="Post",
            body="Content",
            author_id=editor_user.id,
        )

        # Create tags
        tag1 = await create_test_tag(async_db_session, name="python")
        tag2 = await create_test_tag(async_db_session, name="tutorial")

        editor_token = create_access_token({"sub": editor_user.email})
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = client.post(
            "/api/v1/bulk/content/assign-tags",
            json={"content_ids": [content.id], "tag_ids": [tag1.id, tag2.id]},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert "Assigned 2 tags to 1 content items" in data["message"]

        # Verify tags assigned
        await async_db_session.refresh(content)
        assert len(content.tags) == 2

    @pytest.mark.asyncio
    async def test_bulk_assign_tags_unauthorized(self, client, auth_headers):
        """Test bulk assign tags requires editor/admin role"""
        response = client.post(
            "/api/v1/bulk/content/assign-tags",
            json={"content_ids": [1], "tag_ids": [1, 2]},
            headers=auth_headers,  # Regular user
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_update_category(self, client, async_db_session, editor_user):
        """Test bulk updating content category"""
        from app.auth import create_access_token

        # Create category
        category = await create_test_category(async_db_session, name="Tech")

        # Create content
        content_ids = []
        for i in range(2):
            content = await create_test_content(
                async_db_session,
                title=f"Post {i}",
                body="Content",
                author_id=editor_user.id,
            )
            content_ids.append(content.id)

        editor_token = create_access_token({"sub": editor_user.email})
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = client.post(
            "/api/v1/bulk/content/update-category",
            json={"content_ids": content_ids, "category_id": category.id},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert "Updated category to 'Tech'" in data["message"]

        # Verify category updated
        for content_id in content_ids:
            result = await async_db_session.execute(select(Content).where(Content.id == content_id))
            content = result.scalars().first()
            assert content.category_id == category.id

    @pytest.mark.asyncio
    async def test_bulk_update_category_not_found(self, client, editor_user):
        """Test bulk category update handles invalid category"""
        from app.auth import create_access_token

        editor_token = create_access_token({"sub": editor_user.email})
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = client.post(
            "/api/v1/bulk/content/update-category",
            json={"content_ids": [1], "category_id": 99999},
            headers=headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles(self, client, async_db_session, admin_user):
        """Test bulk updating user roles"""
        from app.auth import create_access_token

        # Get roles
        user_role_result = await async_db_session.execute(select(Role).where(Role.name == "user"))
        user_role = user_role_result.scalars().first()

        editor_role_result = await async_db_session.execute(select(Role).where(Role.name == "editor"))
        editor_role = editor_role_result.scalars().first()

        # Create users
        user_ids = []
        for i in range(2):
            user = User(
                email=f"bulkuser{i}@example.com",
                username=f"bulkuser{i}",
                hashed_password="hashed",
                role_id=user_role.id,
            )
            async_db_session.add(user)
            await async_db_session.commit()
            await async_db_session.refresh(user)
            user_ids.append(user.id)

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/users/update-roles",
            json={"user_ids": user_ids, "role_id": editor_role.id},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert "Updated role to 'editor' for 2 users" in data["message"]

        # Verify roles updated
        for user_id in user_ids:
            result = await async_db_session.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            assert user.role_id == editor_role.id

    @pytest.mark.asyncio
    async def test_bulk_update_user_roles_unauthorized(self, client, editor_user):
        """Test bulk update user roles requires admin"""
        from app.auth import create_access_token

        editor_token = create_access_token({"sub": editor_user.email})
        headers = {"Authorization": f"Bearer {editor_token}"}

        response = client.post(
            "/api/v1/bulk/users/update-roles",
            json={"user_ids": [1], "role_id": 2},
            headers=headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_bulk_operations_empty_list(self, client, admin_user):
        """Test bulk operations reject empty content_ids list"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/publish",
            json={"content_ids": []},
            headers=headers,
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_bulk_operations_missing_field(self, client, admin_user):
        """Test bulk operations require all fields"""
        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/update-status",
            json={"content_ids": [1]},  # Missing status field
            headers=headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_bulk_publish_partial_success(self, client, async_db_session, admin_user):
        """Test bulk publish reports partial success correctly"""
        from app.auth import create_access_token

        # Create one pending and one draft content
        pending = await create_test_content(
            async_db_session,
            title="Pending",
            body="Content",
            author_id=admin_user.id,
            status=ContentStatus.PENDING,
        )
        draft = await create_test_content(
            async_db_session,
            title="Draft",
            body="Content",
            author_id=admin_user.id,
            status=ContentStatus.DRAFT,
        )

        admin_token = create_access_token({"sub": admin_user.email})
        headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.post(
            "/api/v1/bulk/content/publish",
            json={"content_ids": [pending.id, draft.id]},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1  # Only pending should succeed
        assert data["failed_count"] == 1
        assert len(data["failed_items"]) == 1
