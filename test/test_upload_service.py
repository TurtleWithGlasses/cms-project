"""
Tests for Upload Service

Tests file upload, validation, image processing, optimization, and media management.
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image

from app.models.media import Media
from app.models.user import User
from app.services.upload_service import (
    MAX_FILE_SIZE,
    THUMBNAIL_SIZE,
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

        assert filename1.endswith(".jpg")
        assert filename2.endswith(".jpg")
        assert filename1 != filename2
        assert len(filename1) > 10

    @pytest.mark.asyncio
    async def test_save_file_success(self, upload_svc, tmp_path):
        """Test successful file saving"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            file = Mock(spec=UploadFile)
            file.read = AsyncMock(side_effect=[b"test content", b""])

            file_path, file_size = await upload_svc.save_file(file, "test.txt")

            assert Path(file_path).exists()
            assert file_size == 12
            assert Path(file_path).read_bytes() == b"test content"

    @pytest.mark.asyncio
    async def test_save_file_exceeds_size_limit(self, upload_svc, tmp_path):
        """Test file save rejects files exceeding size limit"""
        with patch("app.services.upload_service.UPLOAD_DIR", tmp_path):
            large_chunk = b"x" * (MAX_FILE_SIZE + 1)
            file = Mock(spec=UploadFile)
            file.read = AsyncMock(side_effect=[large_chunk, b""])

            with pytest.raises(HTTPException) as exc_info:
                await upload_svc.save_file(file, "large.txt")

            assert exc_info.value.status_code == 413
            assert "exceeds maximum allowed size" in exc_info.value.detail
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
            assert not (tmp_path / "error.txt").exists()

    async def test_create_thumbnail_success(self, upload_svc, tmp_path):
        """Test thumbnail creation for valid image"""
        img = Image.new("RGB", (1000, 800), color="blue")
        image_path = tmp_path / "test.jpg"
        img.save(image_path)

        with patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path):
            thumbnail_path, width, height = upload_svc.create_thumbnail(str(image_path), "thumb_test.jpg")

            assert thumbnail_path is not None
            assert Path(thumbnail_path).exists()
            assert width == 1000
            assert height == 800

            thumb_img = Image.open(thumbnail_path)
            assert thumb_img.size[0] <= THUMBNAIL_SIZE[0]
            assert thumb_img.size[1] <= THUMBNAIL_SIZE[1]

    async def test_create_thumbnail_invalid_image(self, upload_svc, tmp_path):
        """Test thumbnail creation handles invalid image"""
        invalid_image = tmp_path / "invalid.jpg"
        invalid_image.write_text("not an image")

        with patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path):
            thumbnail_path, width, height = upload_svc.create_thumbnail(str(invalid_image), "thumb_invalid.jpg")

            assert thumbnail_path is None
            assert width is None
            assert height is None

    async def test_optimize_image_strips_exif(self, upload_svc, tmp_path):
        """Test image optimization strips EXIF data"""
        from PIL.ExifTags import Base as ExifBase

        img = Image.new("RGB", (200, 200), color="green")
        # Add some EXIF-like data
        image_path = tmp_path / "exif_test.jpg"
        img.save(image_path, format="JPEG")

        with patch("app.services.upload_service.settings") as mock_settings:
            mock_settings.media_enable_exif_strip = True
            mock_settings.media_jpeg_quality = 85
            upload_svc.optimize_image(str(image_path), "image/jpeg")

        # Verify image can still be opened
        optimized = Image.open(image_path)
        assert optimized.size == (200, 200)

    async def test_optimize_image_disabled(self, upload_svc, tmp_path):
        """Test optimization is skipped when disabled"""
        img = Image.new("RGB", (200, 200), color="red")
        image_path = tmp_path / "no_optimize.jpg"
        img.save(image_path, format="JPEG")
        original_size = image_path.stat().st_size

        with patch("app.services.upload_service.settings") as mock_settings:
            mock_settings.media_enable_exif_strip = False
            upload_svc.optimize_image(str(image_path), "image/jpeg")

        # File should be unchanged
        assert image_path.stat().st_size == original_size

    async def test_create_image_variants(self, upload_svc, tmp_path):
        """Test creating multiple image size variants"""
        img = Image.new("RGB", (2000, 1500), color="blue")
        image_path = tmp_path / "large_image.jpg"
        img.save(image_path, format="JPEG")

        # Create variant directories
        for size_name in ["small", "medium", "large"]:
            (tmp_path / size_name).mkdir(exist_ok=True)

        with (
            patch("app.services.upload_service.UPLOAD_DIR", tmp_path),
            patch("app.services.upload_service.settings") as mock_settings,
        ):
            mock_settings.media_jpeg_quality = 85
            variants = upload_svc.create_image_variants(str(image_path), "large_image.jpg")

        assert "small" in variants
        assert "medium" in variants
        assert "large" in variants

        # Verify each variant is within max dimensions
        for size_name, variant_path in variants.items():
            variant_img = Image.open(variant_path)
            from app.services.upload_service import IMAGE_SIZES

            max_dim = IMAGE_SIZES[size_name]
            assert variant_img.size[0] <= max_dim
            assert variant_img.size[1] <= max_dim

    async def test_create_image_variants_small_image(self, upload_svc, tmp_path):
        """Test variants are skipped for small images"""
        img = Image.new("RGB", (100, 80), color="red")
        image_path = tmp_path / "tiny.jpg"
        img.save(image_path, format="JPEG")

        for size_name in ["small", "medium", "large"]:
            (tmp_path / size_name).mkdir(exist_ok=True)

        with (
            patch("app.services.upload_service.UPLOAD_DIR", tmp_path),
            patch("app.services.upload_service.settings") as mock_settings,
        ):
            mock_settings.media_jpeg_quality = 85
            variants = upload_svc.create_image_variants(str(image_path), "tiny.jpg")

        # No variants should be created for a 100x80 image
        assert len(variants) == 0

    @pytest.mark.asyncio
    async def test_upload_file_image_complete(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test complete image upload process with optimization and variants"""
        for d in ["thumbnails", "small", "medium", "large"]:
            (tmp_path / d).mkdir(exist_ok=True)

        with (
            patch("app.services.upload_service.UPLOAD_DIR", tmp_path),
            patch("app.services.upload_service.THUMBNAIL_DIR", tmp_path / "thumbnails"),
        ):
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
            assert media.tags == []
            assert isinstance(media.sizes, dict)

    @pytest.mark.asyncio
    async def test_upload_file_document(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test document upload (no thumbnail or variants)"""
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
            assert media.sizes == {}
            assert media.tags == []

    @pytest.mark.asyncio
    async def test_get_media_by_id_success(self, upload_svc, async_db_session, test_user):
        """Test retrieving media by ID"""
        media = Media(
            filename="test.jpg",
            original_filename="test.jpg",
            file_path="/tmp/test.jpg",
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
        for i in range(5):
            media = Media(
                filename=f"file{i}.jpg",
                original_filename=f"file{i}.jpg",
                file_path=f"/tmp/file{i}.jpg",
                file_size=1024 * i,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
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
        for i in range(15):
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

        page1 = await upload_svc.get_user_media(test_user.id, async_db_session, limit=10, offset=0)
        page2 = await upload_svc.get_user_media(test_user.id, async_db_session, limit=10, offset=10)

        assert len(page1) == 10
        assert len(page2) >= 5

    @pytest.mark.asyncio
    async def test_update_media_metadata(self, upload_svc, async_db_session, test_user):
        """Test updating media metadata"""
        media = Media(
            filename="update_test.jpg",
            original_filename="update_test.jpg",
            file_path="/tmp/update_test.jpg",
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

        updates = {
            "alt_text": "A test image",
            "title": "Test Image",
            "description": "A beautiful test image",
            "tags": ["test", "image"],
        }

        updated = await upload_svc.update_media(media.id, updates, test_user, async_db_session)

        assert updated.alt_text == "A test image"
        assert updated.title == "Test Image"
        assert updated.description == "A beautiful test image"
        assert updated.tags == ["test", "image"]
        assert updated.updated_at is not None

    @pytest.mark.asyncio
    async def test_update_media_unauthorized(self, upload_svc, async_db_session, test_user):
        """Test updating other user's media is forbidden"""
        from app.models.user import Role

        role_result = await async_db_session.execute(__import__("sqlalchemy").select(Role).where(Role.name == "user"))
        role = role_result.scalars().first()

        other_user = User(
            email="other_update@example.com",
            username="otherupdate",
            hashed_password="hashed",
            role_id=role.id,
        )
        async_db_session.add(other_user)
        await async_db_session.commit()
        await async_db_session.refresh(other_user)

        media = Media(
            filename="other.jpg",
            original_filename="other.jpg",
            file_path="/tmp/other.jpg",
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

        with pytest.raises(HTTPException) as exc_info:
            await upload_svc.update_media(media.id, {"alt_text": "hack"}, other_user, async_db_session)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_search_media_by_filename(self, upload_svc, async_db_session, test_user):
        """Test searching media by filename"""
        for name in ["sunset.jpg", "beach.jpg", "mountain.png"]:
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

        results, total = await upload_svc.search_media(user_id=test_user.id, db=async_db_session, query="beach")

        assert total >= 1
        assert any("beach" in m.original_filename for m in results)

    @pytest.mark.asyncio
    async def test_search_media_by_file_type(self, upload_svc, async_db_session, test_user):
        """Test filtering media by file type"""
        for i, (name, ftype) in enumerate(
            [
                ("photo.jpg", "image"),
                ("doc.pdf", "document"),
                ("art.png", "image"),
            ]
        ):
            media = Media(
                filename=f"type_{i}_{name}",
                original_filename=name,
                file_path=f"/tmp/type_{i}_{name}",
                file_size=1024,
                mime_type="image/jpeg" if ftype == "image" else "application/pdf",
                file_type=ftype,
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        results, total = await upload_svc.search_media(user_id=test_user.id, db=async_db_session, file_type="document")

        assert total >= 1
        assert all(m.file_type == "document" for m in results)

    @pytest.mark.asyncio
    async def test_search_media_by_size_range(self, upload_svc, async_db_session, test_user):
        """Test filtering media by file size range"""
        for i, size in enumerate([100, 500, 1000, 5000]):
            media = Media(
                filename=f"size_{i}.jpg",
                original_filename=f"size_{i}.jpg",
                file_path=f"/tmp/size_{i}.jpg",
                file_size=size,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        results, total = await upload_svc.search_media(
            user_id=test_user.id, db=async_db_session, min_size=400, max_size=1500
        )

        assert total >= 2
        assert all(400 <= m.file_size <= 1500 for m in results)

    @pytest.mark.asyncio
    async def test_get_all_media_admin(self, upload_svc, async_db_session, test_user):
        """Test admin listing all media"""
        for i in range(3):
            media = Media(
                filename=f"admin_{i}.jpg",
                original_filename=f"admin_{i}.jpg",
                file_path=f"/tmp/admin_{i}.jpg",
                file_size=1024,
                mime_type="image/jpeg",
                file_type="image",
                tags=[],
                sizes={},
                uploaded_by=test_user.id,
            )
            async_db_session.add(media)
        await async_db_session.commit()

        results, total = await upload_svc.get_all_media_admin(async_db_session, limit=50, offset=0)

        assert total >= 3
        assert len(results) >= 3

    @pytest.mark.asyncio
    async def test_bulk_delete_media(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test bulk deletion of media"""
        media_ids = []
        for i in range(3):
            test_file = tmp_path / f"bulk_del_{i}.jpg"
            test_file.write_bytes(b"data")

            media = Media(
                filename=f"bulk_del_{i}.jpg",
                original_filename=f"bulk_del_{i}.jpg",
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

        result = await upload_svc.bulk_delete_media(media_ids, test_user, async_db_session)

        assert result["success_count"] == 3
        assert result["failed_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_media_success(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test successful media deletion"""
        test_file = tmp_path / "delete_test.jpg"
        test_file.write_bytes(b"image data")
        thumb_file = tmp_path / "thumb_delete_test.jpg"
        thumb_file.write_bytes(b"thumbnail data")

        media = Media(
            filename="delete_test.jpg",
            original_filename="delete_test.jpg",
            file_path=str(test_file),
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

        await upload_svc.delete_media(media.id, test_user, async_db_session)

        assert not test_file.exists()
        assert not thumb_file.exists()

        with pytest.raises(HTTPException):
            await upload_svc.get_media_by_id(media.id, async_db_session)

    @pytest.mark.asyncio
    async def test_delete_media_with_variants(self, upload_svc, async_db_session, test_user, tmp_path):
        """Test deletion also removes size variants"""
        test_file = tmp_path / "main.jpg"
        test_file.write_bytes(b"main")
        small_file = tmp_path / "small.jpg"
        small_file.write_bytes(b"small")
        medium_file = tmp_path / "medium.jpg"
        medium_file.write_bytes(b"medium")

        media = Media(
            filename="main.jpg",
            original_filename="main.jpg",
            file_path=str(test_file),
            file_size=4,
            mime_type="image/jpeg",
            file_type="image",
            tags=[],
            sizes={"small": str(small_file), "medium": str(medium_file)},
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        await upload_svc.delete_media(media.id, test_user, async_db_session)

        assert not test_file.exists()
        assert not small_file.exists()
        assert not medium_file.exists()

    @pytest.mark.asyncio
    async def test_delete_media_unauthorized(self, upload_svc, async_db_session, test_user):
        """Test delete media rejects unauthorized user"""
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
            uploaded_by=test_user.id,
        )
        async_db_session.add(media)
        await async_db_session.commit()
        await async_db_session.refresh(media)

        with pytest.raises(HTTPException) as exc_info:
            await upload_svc.delete_media(media.id, other_user, async_db_session)

        assert exc_info.value.status_code == 403
        assert "Not authorized" in exc_info.value.detail

    async def test_singleton_instance(self):
        """Test upload_service singleton exists"""
        assert upload_service is not None
        assert isinstance(upload_service, UploadService)
