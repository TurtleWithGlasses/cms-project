"""
Tests for Media Folder Service and Routes

Tests CRUD operations for media folder management.
"""

import pytest
from fastapi import HTTPException

from app.models.media import Media
from app.models.media_folder import MediaFolder
from app.models.user import User
from app.services.media_folder_service import MediaFolderService


class TestMediaFolderService:
    """Test media folder service functionality"""

    @pytest.fixture
    def folder_svc(self):
        return MediaFolderService()

    @pytest.mark.asyncio
    async def test_create_folder(self, folder_svc, async_db_session, test_user):
        """Test creating a new folder"""
        folder = await folder_svc.create_folder("My Photos", None, test_user, async_db_session)

        assert folder.id is not None
        assert folder.name == "My Photos"
        assert folder.slug == "my-photos"
        assert folder.parent_id is None
        assert folder.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_subfolder(self, folder_svc, async_db_session, test_user):
        """Test creating a subfolder"""
        parent = await folder_svc.create_folder("Parent", None, test_user, async_db_session)
        child = await folder_svc.create_folder("Child", parent.id, test_user, async_db_session)

        assert child.parent_id == parent.id
        assert child.name == "Child"

    @pytest.mark.asyncio
    async def test_create_subfolder_invalid_parent(self, folder_svc, async_db_session, test_user):
        """Test creating subfolder with non-existent parent"""
        with pytest.raises(HTTPException) as exc_info:
            await folder_svc.create_folder("Orphan", 99999, test_user, async_db_session)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_folders(self, folder_svc, async_db_session, test_user):
        """Test listing user folders"""
        await folder_svc.create_folder("Folder A", None, test_user, async_db_session)
        await folder_svc.create_folder("Folder B", None, test_user, async_db_session)
        await folder_svc.create_folder("Folder C", None, test_user, async_db_session)

        folders = await folder_svc.get_user_folders(test_user.id, async_db_session)

        assert len(folders) >= 3
        names = [f.name for f in folders]
        assert "Folder A" in names
        assert "Folder B" in names
        assert "Folder C" in names

    @pytest.mark.asyncio
    async def test_get_folder_by_id(self, folder_svc, async_db_session, test_user):
        """Test getting folder by ID"""
        folder = await folder_svc.create_folder("Get Test", None, test_user, async_db_session)
        result = await folder_svc.get_folder_by_id(folder.id, test_user, async_db_session)

        assert result.id == folder.id
        assert result.name == "Get Test"

    @pytest.mark.asyncio
    async def test_get_folder_not_found(self, folder_svc, async_db_session, test_user):
        """Test getting non-existent folder"""
        with pytest.raises(HTTPException) as exc_info:
            await folder_svc.get_folder_by_id(99999, test_user, async_db_session)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_folder_forbidden(self, folder_svc, async_db_session, test_user):
        """Test accessing another user's folder"""
        from app.models.user import Role

        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(
            email="folder_other@example.com",
            username="folderother",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        folder = await folder_svc.create_folder("Private", None, test_user, async_db_session)

        with pytest.raises(HTTPException) as exc_info:
            await folder_svc.get_folder_by_id(folder.id, other_user, async_db_session)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_update_folder(self, folder_svc, async_db_session, test_user):
        """Test renaming a folder"""
        folder = await folder_svc.create_folder("Old Name", None, test_user, async_db_session)
        updated = await folder_svc.update_folder(folder.id, "New Name", test_user, async_db_session)

        assert updated.name == "New Name"
        assert updated.slug == "new-name"

    @pytest.mark.asyncio
    async def test_delete_folder(self, folder_svc, async_db_session, test_user):
        """Test deleting a folder"""
        folder = await folder_svc.create_folder("To Delete", None, test_user, async_db_session)
        folder_id = folder.id

        await folder_svc.delete_folder(folder_id, test_user, async_db_session)

        with pytest.raises(HTTPException) as exc_info:
            await folder_svc.get_folder_by_id(folder_id, test_user, async_db_session)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_folder_moves_media_to_root(self, folder_svc, async_db_session, test_user):
        """Test deleting a folder moves contained media to root"""
        folder = await folder_svc.create_folder("Media Folder", None, test_user, async_db_session)

        media = Media(
            filename="in_folder.jpg",
            original_filename="in_folder.jpg",
            file_path="/tmp/in_folder.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            folder_id=folder.id,
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)
        media_id = media.id

        await folder_svc.delete_folder(folder.id, test_user, async_db_session)

        # Refresh media to see updated folder_id
        await async_db_session.refresh(media)
        assert media.folder_id is None

    @pytest.mark.asyncio
    async def test_delete_folder_moves_subfolders_to_parent(self, folder_svc, async_db_session, test_user):
        """Test deleting a folder moves subfolders to parent"""
        parent = await folder_svc.create_folder("Parent", None, test_user, async_db_session)
        child = await folder_svc.create_folder("Child", parent.id, test_user, async_db_session)
        grandchild = await folder_svc.create_folder("Grandchild", child.id, test_user, async_db_session)

        await folder_svc.delete_folder(child.id, test_user, async_db_session)

        # Grandchild should now be under parent
        await async_db_session.refresh(grandchild)
        assert grandchild.parent_id == parent.id


class TestMediaFolderRoutes:
    """Test media folder API endpoints"""

    @pytest.mark.asyncio
    async def test_create_folder_endpoint(self, client, auth_headers):
        """Test creating a folder via API"""
        response = client.post(
            "/api/v1/media/folders/",
            json={"name": "Test Folder"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Folder"
        assert data["slug"] == "test-folder"

    @pytest.mark.asyncio
    async def test_list_folders_endpoint(self, client, auth_headers):
        """Test listing folders via API"""
        # Create some folders
        client.post("/api/v1/media/folders/", json={"name": "Folder 1"}, headers=auth_headers)
        client.post("/api/v1/media/folders/", json={"name": "Folder 2"}, headers=auth_headers)

        response = client.get("/api/v1/media/folders/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["folders"]) >= 2

    @pytest.mark.asyncio
    async def test_get_folder_endpoint(self, client, auth_headers):
        """Test getting a folder by ID"""
        create_response = client.post("/api/v1/media/folders/", json={"name": "Get Me"}, headers=auth_headers)
        folder_id = create_response.json()["id"]

        response = client.get(f"/api/v1/media/folders/{folder_id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["name"] == "Get Me"

    @pytest.mark.asyncio
    async def test_update_folder_endpoint(self, client, auth_headers):
        """Test renaming a folder"""
        create_response = client.post("/api/v1/media/folders/", json={"name": "Old"}, headers=auth_headers)
        folder_id = create_response.json()["id"]

        response = client.patch(
            f"/api/v1/media/folders/{folder_id}",
            json={"name": "New"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "New"

    @pytest.mark.asyncio
    async def test_delete_folder_endpoint(self, client, auth_headers):
        """Test deleting a folder"""
        create_response = client.post("/api/v1/media/folders/", json={"name": "Delete Me"}, headers=auth_headers)
        folder_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/media/folders/{folder_id}", headers=auth_headers)

        assert response.status_code == 204
