"""
Tests for Media Routes

Tests API endpoints for file upload and media management.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi import UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.user import User


class TestMediaRoutes:
    """Test media API endpoints"""

    @pytest.fixture
    def mock_upload_service(self):
        """Mock upload service for testing"""
        with patch("app.routes.media.upload_service") as mock:
            yield mock

    def create_test_image_bytes(self, width=100, height=100):
        """Helper to create test image bytes"""
        img = Image.new("RGB", (width, height), color="blue")
        img_bytes = BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        return img_bytes

    @pytest.mark.asyncio
    async def test_upload_file_success(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test successful file upload"""
        for d in ["thumbnails", "small", "medium", "large"]:
            (tmp_path / d).mkdir(exist_ok=True)

        with (
            patch("app.services.upload_service.UPLOAD_DIR", tmp_path),
            patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path / "thumbnails"),
        ):
            img_bytes = self.create_test_image_bytes()

            files = {"file": ("test.jpg", img_bytes, "image/jpeg")}
            response = client.post("/api/v1/media/upload", files=files, headers=auth_headers)

            assert response.status_code == 201
            data = response.json()
            assert data["original_filename"] == "test.jpg"
            assert data["file_type"] == "image"
            assert data["mime_type"] == "image/jpeg"
            assert "url" in data
            assert data["width"] == 100
            assert data["height"] == 100
            assert "tags" in data
            assert "sizes" in data

    @pytest.mark.asyncio
    async def test_upload_file_unauthorized(self, client):
        """Test upload requires authentication"""
        img_bytes = BytesIO(b"fake image")
        files = {"file": ("test.jpg", img_bytes, "image/jpeg")}

        response = client.post("/api/v1/media/upload", files=files)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_file_invalid_type(self, client, auth_headers):
        """Test upload rejects invalid file type"""
        file_bytes = BytesIO(b"fake executable")
        files = {"file": ("malware.exe", file_bytes, "application/x-msdownload")}

        response = client.post("/api/v1/media/upload", files=files, headers=auth_headers)

        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_document(self, client, auth_headers, tmp_path):
        """Test document upload"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            pdf_bytes = BytesIO(b"%PDF-1.4 fake pdf content")
            files = {"file": ("document.pdf", pdf_bytes, "application/pdf")}

            response = client.post("/api/v1/media/upload", files=files, headers=auth_headers)

            assert response.status_code == 201
            data = response.json()
            assert data["file_type"] == "document"
            assert data["mime_type"] == "application/pdf"
            assert data["thumbnail_url"] is None

    @pytest.mark.asyncio
    async def test_list_media(self, client, auth_headers, async_db_session, test_user):
        """Test listing user's media"""
        for i in range(3):
            media = Media(
                filename=f"file{i}.jpg",
                original_filename=f"file{i}.jpg",
                file_path=f"/tmp/file{i}.jpg",
                file_size=1024,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        response = client.get("/api/v1/media/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["media"]) >= 3
        assert data["limit"] == 50
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_media_pagination(self, client, auth_headers, async_db_session, test_user):
        """Test media listing pagination"""
        for i in range(25):
            media = Media(
                filename=f"page{i}.jpg",
                original_filename=f"page{i}.jpg",
                file_path=f"/tmp/page{i}.jpg",
                file_size=1024,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        response1 = client.get("/api/v1/media/?limit=10&offset=0", headers=auth_headers)
        response2 = client.get("/api/v1/media/?limit=10&offset=10", headers=auth_headers)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        assert len(data1["media"]) == 10
        assert len(data2["media"]) >= 10

    @pytest.mark.asyncio
    async def test_list_media_limit_enforcement(self, client, auth_headers):
        """Test max limit enforcement"""
        response = client.get("/api/v1/media/?limit=200", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 100

    @pytest.mark.asyncio
    async def test_get_media_by_id(self, client, auth_headers, async_db_session, test_user):
        """Test getting media by ID"""
        media = Media(
            filename="get_test.jpg",
            original_filename="get_test.jpg",
            file_path="/tmp/get_test.jpg",
            file_size=2048,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/{media.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == media.id
        assert data["filename"] == "get_test.jpg"

    @pytest.mark.asyncio
    async def test_get_media_not_found(self, client, auth_headers):
        """Test get media returns 404 for non-existent ID"""
        response = client.get("/api/v1/media/99999", headers=auth_headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_media_forbidden(self, client, async_db_session, test_user):
        """Test user cannot access other user's media"""
        from app.models.user import Role

        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        media = Media(
            filename="private.jpg",
            original_filename="private.jpg",
            file_path="/tmp/private.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=other_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        from app.auth import create_access_token

        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/v1/media/{media.id}", headers=headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_media_endpoint(self, client, auth_headers, async_db_session, test_user):
        """Test updating media metadata via PATCH"""
        media = Media(
            filename="patch_test.jpg",
            original_filename="patch_test.jpg",
            file_path="/tmp/patch_test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.patch(
            f"/api/v1/media/{media.id}",
            json={
                "alt_text": "Beautiful sunset",
                "title": "Sunset Photo",
                "tags": ["nature", "sunset"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["alt_text"] == "Beautiful sunset"
        assert data["title"] == "Sunset Photo"
        assert data["tags"] == ["nature", "sunset"]

    @pytest.mark.asyncio
    async def test_search_media_endpoint(self, client, auth_headers, async_db_session, test_user):
        """Test media search endpoint"""
        for name in ["sunset_search.jpg", "beach_search.jpg", "mountain_search.png"]:
            media = Media(
                filename=name,
                original_filename=name,
                file_path=f"/tmp/{name}",
                file_size=1024,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        response = client.get("/api/v1/media/search?query=beach_search", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_download_file(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test downloading file"""
        test_file = tmp_path / "download.jpg"
        test_file.write_bytes(b"image content")

        media = Media(
            filename="download.jpg",
            original_filename="download.jpg",
            file_path=str(test_file),
            file_size=13,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/files/{media.id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.content == b"image content"

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, client, auth_headers, async_db_session, test_user):
        """Test download returns 404 when file missing on disk"""
        media = Media(
            filename="missing.jpg",
            original_filename="missing.jpg",
            file_path="/nonexistent/missing.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/files/{media.id}", headers=auth_headers)

        assert response.status_code == 404
        assert "not found on disk" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_thumbnail(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test getting thumbnail"""
        thumb_file = tmp_path / "thumb.jpg"
        thumb_file.write_bytes(b"thumbnail content")

        media = Media(
            filename="image.jpg",
            original_filename="image.jpg",
            file_path=str(tmp_path / "image.jpg"),
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            thumbnail_path=str(thumb_file),
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/thumbnails/{media.id}", headers=auth_headers)

        assert response.status_code == 200
        assert response.content == b"thumbnail content"

    @pytest.mark.asyncio
    async def test_get_thumbnail_not_available(self, client, auth_headers, async_db_session, test_user):
        """Test thumbnail returns 404 for non-image media"""
        media = Media(
            filename="document.pdf",
            original_filename="document.pdf",
            file_path="/tmp/document.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_type="document",
            thumbnail_path=None,
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/thumbnails/{media.id}", headers=auth_headers)

        assert response.status_code == 404
        assert "No thumbnail available" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_image_size_variant(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test getting image size variant"""
        small_file = tmp_path / "small.jpg"
        small_file.write_bytes(b"small variant")

        media = Media(
            filename="sized.jpg",
            original_filename="sized.jpg",
            file_path=str(tmp_path / "sized.jpg"),
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={"small": str(small_file)},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/sizes/{media.id}/small", headers=auth_headers)

        assert response.status_code == 200
        assert response.content == b"small variant"

    @pytest.mark.asyncio
    async def test_get_image_size_invalid(self, client, auth_headers, async_db_session, test_user):
        """Test invalid size name returns 400"""
        media = Media(
            filename="sized2.jpg",
            original_filename="sized2.jpg",
            file_path="/tmp/sized2.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.get(f"/api/v1/media/sizes/{media.id}/huge", headers=auth_headers)

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_bulk_delete_endpoint(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test bulk delete endpoint"""
        media_ids = []
        for i in range(3):
            test_file = tmp_path / f"bulk_rt_{i}.jpg"
            test_file.write_bytes(b"data")

            media = Media(
                filename=f"bulk_rt_{i}.jpg",
                original_filename=f"bulk_rt_{i}.jpg",
                file_path=str(test_file),
                file_size=4,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
            await async_db_session.commit()
            await async_db_session.refresh(media)
            media_ids.append(media.id)

        response = client.post(
            "/api/v1/media/bulk-delete",
            json={"media_ids": media_ids},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_media(self, client, auth_headers, async_db_session, test_user, tmp_path):
        """Test deleting media"""
        test_file = tmp_path / "delete.jpg"
        test_file.write_bytes(b"delete me")

        media = Media(
            filename="delete.jpg",
            original_filename="delete.jpg",
            file_path=str(test_file),
            file_size=9,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        response = client.delete(f"/api/v1/media/{media.id}", headers=auth_headers)

        assert response.status_code == 204
        assert not test_file.exists()

    @pytest.mark.asyncio
    async def test_delete_media_forbidden(self, client, async_db_session, test_user):
        """Test user cannot delete other user's media"""
        from app.models.user import Role

        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(
            email="other_delete@example.com",
            username="otherdelete",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        media = Media(
            filename="protected.jpg",
            original_filename="protected.jpg",
            file_path="/tmp/protected.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=other_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        from app.auth import create_access_token

        token = create_access_token({"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete(f"/api/v1/media/{media.id}", headers=headers)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_access_any_media(self, client, async_db_session, test_user):
        """Test admin can access any user's media"""
        from app.models.user import Role

        admin_role_result = await async_db_session.execute(
            __import__("sqlalchemy").select(Role).where(Role.name == "admin")
        )
        admin_role = admin_role_result.scalars().first()

        admin_user = User(
            email="admin@example.com",
            username="adminuser",
            hashed_password="hashed",
            role_id=admin_role.id,
        )
        async_db_session.add(admin_user)
        await async_db_session.commit()
        await async_db_session.refresh(admin_user)

        media = Media(
            filename="user_media.jpg",
            original_filename="user_media.jpg",
            file_path="/tmp/user_media.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        from app.auth import create_access_token

        admin_token = create_access_token({"sub": admin_user.email})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        response = client.get(f"/api/v1/media/{media.id}", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == media.id
