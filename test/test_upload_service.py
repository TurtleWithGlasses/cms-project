"""
Tests for Upload Service

Tests file upload, validation, image processing, and media management.
"""

import os
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.user import User
from app.services.upload_service import (
    MAX_FILE_SIZE,
    THUMBNAIL_SIZE,
    UPLOAD_DIR,
    UploadService,
    upload_service,
)


class TestUploadService:
    """Test upload service functionality"""

    @pytest.fixture
    def upload_svc(self):
        """Create upload service instance"""
        return UploadService()

    @pytest.fixture
    def mock_image_file(self):
        """Create a mock image upload file"""
        # Create a simple test image
        img = Image.new("RGB", (800, 600), color="red")
        img_bytes = BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        file = Mock(spec=UploadFile)
        file.filename = "test_image.png"
        file.content_type = "image/png"
        file.read = AsyncMock(side_effect=[img_bytes.read(), b""])
        return file

    @pytest.fixture
    def mock_document_file(self):
        """Create a mock document upload file"""
        file = Mock(spec=UploadFile)
        file.filename = "test_document.pdf"
        file.content_type = "application/pdf"
        file.read = AsyncMock(side_effect=[b"fake pdf content", b""])
        return file

    async def test_validate_file_valid_image(self, upload_svc):
        """Test validation accepts valid image file"""
        file = Mock(spec=UploadFile)
        file.filename = "image.jpg"
        file.content_type = "image/jpeg"

        file_type, mime_type = upload_svc.validate_file(file)

        assert file_type == "image"
        assert mime_type == "image/jpeg"

    async def test_validate_file_valid_document(self, upload_svc):
        """Test validation accepts valid document file"""
        file = Mock(spec=UploadFile)
        file.filename = "document.pdf"
        file.content_type = "application/pdf"

        file_type, mime_type = upload_svc.validate_file(file)

        assert file_type == "document"
        assert mime_type == "application/pdf"

    async def test_validate_file_no_filename(self, upload_svc):
        """Test validation rejects file without filename"""
        file = Mock(spec=UploadFile)
        file.filename = None
        file.content_type = "image/png"

        with pytest.raises(HTTPException) as exc_info:
            upload_svc.validate_file(file)

        assert exc_info.value.status_code == 400
        assert "No file provided" in exc_info.value.detail

    async def test_validate_file_invalid_mime_type(self, upload_svc):
        """Test validation rejects invalid MIME type"""
        file = Mock(spec=UploadFile)
        file.filename = "malicious.exe"
        file.content_type = "application/x-msdownload"

        with pytest.raises(HTTPException) as exc_info:
            upload_svc.validate_file(file)

        assert exc_info.value.status_code == 400
        assert "File type not allowed" in exc_info.value.detail

    async def test_validate_file_extension_mismatch(self, upload_svc):
        """Test validation rejects extension that doesn't match MIME type"""
        file = Mock(spec=UploadFile)
        file.filename = "image.txt"
        file.content_type = "image/png"

        with pytest.raises(HTTPException) as exc_info:
            upload_svc.validate_file(file)

        assert exc_info.value.status_code == 400
        assert "does not match MIME type" in exc_info.value.detail

    async def test_generate_unique_filename(self, upload_svc):
        """Test unique filename generation"""
        filename1 = upload_svc.generate_unique_filename("test.jpg")
        filename2 = upload_svc.generate_unique_filename("test.jpg")

        # Should preserve extension
        assert filename1.endswith(".jpg")
        assert filename2.endswith(".jpg")

        # Should be unique
        assert filename1 != filename2

        # Should contain UUID
        assert len(filename1) > 10

    @pytest.mark.asyncio
    async def test_save_file_success(self, upload_svc, tmp_path):
        """Test successful file saving"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            file = Mock(spec=UploadFile)
            file.read = AsyncMock(side_effect=[b"test content", b""])

            file_path, file_size = await upload_svc.save_file(file, "test.txt")

            assert Path(file_path).exists()
            assert file_size == 12  # len("test content")
            assert Path(file_path).read_bytes() == b"test content"

    @pytest.mark.asyncio
    async def test_save_file_exceeds_size_limit(self, upload_svc, tmp_path):
        """Test file save rejects files exceeding size limit"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            # Create mock file that exceeds size limit
            large_chunk = b"x" * (MAX_FILE_SIZE + 1)
            file = Mock(spec=UploadFile)
            file.read = AsyncMock(side_effect=[large_chunk, b""])

            with pytest.raises(HTTPException) as exc_info:
                await upload_svc.save_file(file, "large.txt")

            assert exc_info.value.status_code == 413
            assert "exceeds maximum allowed size" in exc_info.value.detail

            # Verify cleanup - file should not exist
            assert not (tmp_path / "large.txt").exists()

    @pytest.mark.asyncio
    async def test_save_file_cleanup_on_error(self, upload_svc, tmp_path):
        """Test file cleanup when save fails"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            file = Mock(spec=UploadFile)
            file.read = AsyncMock(side_effect=Exception("Read error"))

            with pytest.raises(HTTPException) as exc_info:
                await upload_svc.save_file(file, "error.txt")

            assert exc_info.value.status_code == 500
            assert "Failed to save file" in exc_info.value.detail

            # Verify cleanup
            assert not (tmp_path / "error.txt").exists()

    async def test_create_thumbnail_success(self, upload_svc, tmp_path):
        """Test thumbnail creation for valid image"""
        # Create test image
        img = Image.new("RGB", (1000, 800), color="blue")
        image_path = tmp_path / "test.jpg"
        img.save(image_path)

        with patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path):
            thumbnail_path, width, height = upload_svc.create_thumbnail(str(image_path), "thumb_test.jpg")

            assert thumbnail_path is not None
            assert Path(thumbnail_path).exists()
            assert width == 1000
            assert height == 800

            # Verify thumbnail size
            thumb_img = Image.open(thumbnail_path)
            assert thumb_img.size[0] <= THUMBNAIL_SIZE[0]
            assert thumb_img.size[1] <= THUMBNAIL_SIZE[1]

    async def test_create_thumbnail_invalid_image(self, upload_svc, tmp_path):
        """Test thumbnail creation handles invalid image"""
        # Create invalid image file
        invalid_image = tmp_path / "invalid.jpg"
        invalid_image.write_text("not an image")

        with patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path):
            thumbnail_path, width, height = upload_svc.create_thumbnail(str(invalid_image), "thumb_invalid.jpg")

            assert thumbnail_path is None
            assert width is None
            assert height is None

    @pytest.mark.asyncio
    async def test_upload_file_image_complete(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test complete image upload process"""
        with (
            patch("app.services.upload_service.UPLOAD_DIR", tmp_path),
            patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path),
        ):
            # Create test image
            img = Image.new("RGB", (640, 480), color="green")
            img_bytes = BytesIO()
            img.save(img_bytes, format="JPEG")
            img_bytes.seek(0)

            file = Mock(spec=UploadFile)
            file.filename = "photo.jpg"
            file.content_type = "image/jpeg"
            file.read = AsyncMock(side_effect=[img_bytes.read(), b""])

            media = await upload_svc.upload_file(file, test_user, async_db_session)

            assert media.id is not None
            assert media.original_filename == "photo.jpg"
            assert media.file_type == "image"
            assert media.mime_type == "image/jpeg"
            assert media.uploaded_by == test_user.id
            assert media.width == 640
            assert media.height == 480
            assert media.thumbnail_path is not None

    @pytest.mark.asyncio
    async def test_upload_file_document(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test document upload (no thumbnail)"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            file = Mock(spec=UploadFile)
            file.filename = "document.pdf"
            file.content_type = "application/pdf"
            file.read = AsyncMock(side_effect=[b"PDF content here", b""])

            media = await upload_svc.upload_file(file, test_user, async_db_session)

            assert media.file_type == "document"
            assert media.mime_type == "application/pdf"
            assert media.thumbnail_path is None
            assert media.width is None
            assert media.height is None

    @pytest.mark.asyncio
    async def test_get_media_by_id_success(self, upload_svc, async_db_session, test_user):
        """Test retrieving media by ID"""
        # Create test media
        media = Media(
            filename="test.jpg",
            original_filename="test.jpg",
            file_path="/tmp/test.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        result = await upload_svc.get_media_by_id(media.id, async_db_session)

        assert result.id == media.id
        assert result.filename == "test.jpg"

    @pytest.mark.asyncio
    async def test_get_media_by_id_not_found(self, upload_svc, async_db_session):
        """Test get media returns 404 for non-existent ID"""
        with pytest.raises(HTTPException) as exc_info:
            await upload_svc.get_media_by_id(99999, async_db_session)

        assert exc_info.value.status_code == 404
        assert "Media not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_user_media(self, upload_svc, async_db_session, test_user):
        """Test retrieving all media for a user"""
        # Create multiple media items
        for i in range(5):
            media = Media(
                filename=f"file{i}.jpg",
                original_filename=f"file{i}.jpg",
                file_path=f"/tmp/file{i}.jpg",
                file_size=1024 * i,
                mime_type="image/jpeg",
                file_type="image",
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        results = await upload_svc.get_user_media(test_user.id, async_db_session, limit=10, offset=0)

        assert len(results) >= 5
        assert all(m.uploaded_by == test_user.id for m in results)

    @pytest.mark.asyncio
    async def test_get_user_media_pagination(self, upload_svc, async_db_session, test_user):
        """Test media pagination"""
        # Create 15 media items
        for i in range(15):
            media = Media(
                filename=f"page{i}.jpg",
                original_filename=f"page{i}.jpg",
                file_path=f"/tmp/page{i}.jpg",
                file_size=1024,
                mime_type="image/jpeg",
                file_type="image",
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        # Get first page
        page1 = await upload_svc.get_user_media(test_user.id, async_db_session, limit=10, offset=0)
        # Get second page
        page2 = await upload_svc.get_user_media(test_user.id, async_db_session, limit=10, offset=10)

        assert len(page1) == 10
        assert len(page2) >= 5

    @pytest.mark.asyncio
    async def test_delete_media_success(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test successful media deletion"""
        # Create test files
        test_file = tmp_path / "delete_test.jpg"
        test_file.write_bytes(b"image data")
        thumb_file = tmp_path / "thumb_delete_test.jpg"
        thumb_file.write_bytes(b"thumbnail data")

        # Create media record
        media = Media(
            filename="delete_test.jpg",
            original_filename="delete_test.jpg",
            file_path=str(test_file),
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            thumbnail_path=str(thumb_file),
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        # Delete media
        await upload_svc.delete_media(media.id, test_user, async_db_session)

        # Verify files deleted
        assert not test_file.exists()
        assert not thumb_file.exists()

        # Verify database record deleted
        with pytest.raises(HTTPException):
            await upload_svc.get_media_by_id(media.id, async_db_session)

    @pytest.mark.asyncio
    async def test_delete_media_unauthorized(self, upload_svc, async_db_session, test_user):
        """Test delete media rejects unauthorized user"""
        from app.models.user import Role

        # Create another user
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

        # Create media owned by test_user
        media = Media(
            filename="private.jpg",
            original_filename="private.jpg",
            file_path="/tmp/private.jpg",
            file_size=1024,
            mime_type="image/jpeg",
            file_type="image",
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        # Try to delete with other_user
        with pytest.raises(HTTPException) as exc_info:
            await upload_svc.delete_media(media.id, other_user, async_db_session)

        assert exc_info.value.status_code == 403
        assert "Not authorized" in exc_info.value.detail

    async def test_singleton_instance(self):
        """Test upload_service singleton exists"""
        assert upload_service is not None
        assert isinstance(upload_service, UploadService)
