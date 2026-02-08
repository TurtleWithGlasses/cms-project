"""
Upload Service

Handles file uploads, validation, image processing, optimization, and storage.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.media import Media
from app.models.user import User

logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = Path("uploads")
THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"
MAX_FILE_SIZE = settings.media_max_file_size
THUMBNAIL_SIZE = (300, 300)

# Image variant sizes (max dimension)
IMAGE_SIZES = {
    "small": 150,
    "medium": 600,
    "large": 1200,
}

# Allowed file types
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": [".pdf"],
    "application/msword": [".doc"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/vnd.ms-excel": [".xls"],
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    "text/plain": [".txt"],
    "text/markdown": [".md"],
}

ALLOWED_MIME_TYPES = {**ALLOWED_IMAGE_TYPES, **ALLOWED_DOCUMENT_TYPES}


class UploadService:
    """Service for handling file uploads and media management"""

    def __init__(self):
        """Initialize upload directories"""
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
        # Create variant directories
        for size_name in IMAGE_SIZES:
            (UPLOAD_DIR / size_name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_file(file: UploadFile) -> tuple[str, str]:
        """
        Validate uploaded file.

        Args:
            file: Uploaded file

        Returns:
            Tuple of (file_type, validated_mime_type)

        Raises:
            HTTPException: If file is invalid
        """
        # Check file exists
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

        # Check MIME type
        mime_type = file.content_type
        if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES.keys())}",
            )

        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        allowed_extensions = ALLOWED_MIME_TYPES[mime_type]
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension {file_ext} does not match MIME type {mime_type}",
            )

        # Determine file type category
        if mime_type in ALLOWED_IMAGE_TYPES:
            file_type = "image"
        elif mime_type in ALLOWED_DOCUMENT_TYPES:
            file_type = "document"
        else:
            file_type = "other"

        return file_type, mime_type

    @staticmethod
    def generate_unique_filename(original_filename: str) -> str:
        """
        Generate a unique filename to prevent collisions.

        Args:
            original_filename: Original filename

        Returns:
            Unique filename with UUID prefix
        """
        file_ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_ext}"

    @staticmethod
    async def save_file(file: UploadFile, filename: str) -> tuple[str, int]:
        """
        Save uploaded file to disk.

        Args:
            file: Uploaded file
            filename: Filename to save as

        Returns:
            Tuple of (file_path, file_size)

        Raises:
            HTTPException: If file save fails or exceeds size limit
        """
        file_path = UPLOAD_DIR / filename
        file_size = 0

        try:
            with file_path.open("wb") as buffer:
                while chunk := await file.read(8192):
                    file_size += len(chunk)

                    # Check file size limit
                    if file_size > MAX_FILE_SIZE:
                        # Clean up partial file
                        buffer.close()
                        file_path.unlink()
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB",
                        )

                    buffer.write(chunk)

            return str(file_path), file_size

        except HTTPException:
            raise
        except Exception as e:
            # Clean up on error
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {str(e)}"
            ) from e

    @staticmethod
    def create_thumbnail(image_path: str, thumbnail_filename: str) -> tuple[str | None, int | None, int | None]:
        """
        Create thumbnail for an image.

        Args:
            image_path: Path to original image
            thumbnail_filename: Filename for thumbnail

        Returns:
            Tuple of (thumbnail_path, original_width, original_height)
        """
        try:
            with Image.open(image_path) as img:
                original_width, original_height = img.size

                # Create thumbnail
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save thumbnail
                thumbnail_path = THUMBNAIL_DIR / thumbnail_filename
                img.save(thumbnail_path, optimize=True, quality=85)

                return str(thumbnail_path), original_width, original_height

        except Exception as e:
            logger.warning("Failed to create thumbnail: %s", e)
            return None, None, None

    @staticmethod
    def optimize_image(image_path: str, mime_type: str) -> None:
        """
        Optimize an image: strip EXIF metadata and compress.

        Args:
            image_path: Path to the image file
            mime_type: MIME type of the image
        """
        if not settings.media_enable_exif_strip:
            return

        try:
            with Image.open(image_path) as img:
                # Strip EXIF by creating a new image without metadata
                data = list(img.getdata())
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(data)

                save_kwargs: dict = {"optimize": True}
                if mime_type in ("image/jpeg", "image/jpg"):
                    save_kwargs["quality"] = settings.media_jpeg_quality
                elif mime_type == "image/png":
                    save_kwargs["compress_level"] = settings.media_png_compression
                elif mime_type == "image/webp":
                    save_kwargs["quality"] = 80

                clean_img.save(image_path, **save_kwargs)
        except Exception as e:
            logger.warning("Failed to optimize image: %s", e)

    @staticmethod
    def create_image_variants(image_path: str, filename: str) -> dict[str, str]:
        """
        Create multiple size variants of an image.

        Args:
            image_path: Path to the original image
            filename: Base filename for variants

        Returns:
            Dict mapping size name to file path
        """
        variants: dict[str, str] = {}

        try:
            with Image.open(image_path) as img:
                original_width, original_height = img.size

                for size_name, max_dim in IMAGE_SIZES.items():
                    # Skip if original is smaller than target
                    if original_width <= max_dim and original_height <= max_dim:
                        continue

                    variant = img.copy()
                    variant.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                    variant_path = UPLOAD_DIR / size_name / filename
                    save_kwargs: dict = {"optimize": True, "quality": settings.media_jpeg_quality}
                    variant.save(variant_path, **save_kwargs)
                    variants[size_name] = str(variant_path)

        except Exception as e:
            logger.warning("Failed to create image variants: %s", e)

        return variants

    async def upload_file(self, file: UploadFile, current_user: User, db: AsyncSession) -> Media:
        """
        Handle complete file upload process.

        Args:
            file: Uploaded file
            current_user: User uploading the file
            db: Database session

        Returns:
            Media: Created media object

        Raises:
            HTTPException: If upload fails
        """
        # Validate file
        file_type, mime_type = self.validate_file(file)

        # Generate unique filename
        unique_filename = self.generate_unique_filename(file.filename)

        # Save file
        file_path, file_size = await self.save_file(file, unique_filename)

        # Process image (optimize, create thumbnail, create variants)
        thumbnail_path = None
        width = None
        height = None
        sizes: dict[str, str] = {}

        if file_type == "image":
            # Optimize image (strip EXIF, compress)
            self.optimize_image(file_path, mime_type)

            # Create thumbnail
            thumbnail_filename = f"thumb_{unique_filename}"
            thumbnail_path, width, height = self.create_thumbnail(file_path, thumbnail_filename)

            # Create size variants
            sizes = self.create_image_variants(file_path, unique_filename)

        # Create media record
        media = Media(
            filename=unique_filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            file_type=file_type,
            width=width,
            height=height,
            thumbnail_path=thumbnail_path,
            sizes=sizes,
            tags=[],
            uploaded_by=current_user.id,
        )

        db.add(media)
        await db.commit()
        await db.refresh(media)

        return media

    @staticmethod
    async def get_media_by_id(media_id: int, db: AsyncSession) -> Media:
        """
        Get media by ID.

        Args:
            media_id: Media ID
            db: Database session

        Returns:
            Media object

        Raises:
            HTTPException: If media not found
        """
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalars().first()

        if not media:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

        return media

    @staticmethod
    async def get_user_media(user_id: int, db: AsyncSession, limit: int = 50, offset: int = 0) -> list[Media]:
        """
        Get all media uploaded by a user.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of Media objects
        """
        stmt = (
            select(Media)
            .where(Media.uploaded_by == user_id)
            .order_by(Media.uploaded_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_media(media_id: int, updates: dict, current_user: User, db: AsyncSession) -> Media:
        """
        Update media metadata.

        Args:
            media_id: Media ID
            updates: Dict of fields to update
            current_user: User making the update
            db: Database session

        Returns:
            Updated Media object
        """
        media = await UploadService.get_media_by_id(media_id, db)

        # Check ownership
        from app.constants.roles import RoleEnum

        if media.uploaded_by != current_user.id and current_user.role.name not in [
            RoleEnum.ADMIN.value,
            RoleEnum.SUPERADMIN.value,
        ]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this media")

        # Validate folder belongs to user if provided
        if "folder_id" in updates and updates["folder_id"] is not None:
            from app.models.media_folder import MediaFolder

            folder_result = await db.execute(select(MediaFolder).where(MediaFolder.id == updates["folder_id"]))
            folder = folder_result.scalars().first()
            if not folder:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
            if folder.user_id != current_user.id and current_user.role.name not in [
                RoleEnum.ADMIN.value,
                RoleEnum.SUPERADMIN.value,
            ]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this folder")

        # Apply updates
        for field, value in updates.items():
            if hasattr(media, field):
                setattr(media, field, value)

        media.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(media)

        return media

    @staticmethod
    async def search_media(
        user_id: int,
        db: AsyncSession,
        query: str | None = None,
        file_type: str | None = None,
        folder_id: int | None = None,
        tags: list[str] | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        uploaded_after: datetime | None = None,
        uploaded_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Media], int]:
        """
        Search and filter media for a user.

        Returns:
            Tuple of (results, total_count)
        """
        stmt = select(Media).where(Media.uploaded_by == user_id)
        count_stmt = select(func.count(Media.id)).where(Media.uploaded_by == user_id)

        # Text search
        if query:
            search_filter = or_(
                func.lower(Media.original_filename).contains(query.lower()),
                func.lower(Media.alt_text).contains(query.lower()),
                func.lower(Media.title).contains(query.lower()),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # File type filter
        if file_type:
            stmt = stmt.where(Media.file_type == file_type)
            count_stmt = count_stmt.where(Media.file_type == file_type)

        # Folder filter
        if folder_id is not None:
            stmt = stmt.where(Media.folder_id == folder_id)
            count_stmt = count_stmt.where(Media.folder_id == folder_id)

        # Tags filter (check each tag exists in the JSON array)
        if tags:
            for tag in tags:
                tag_filter = Media.tags.contains(tag)
                stmt = stmt.where(tag_filter)
                count_stmt = count_stmt.where(tag_filter)

        # Size range
        if min_size is not None:
            stmt = stmt.where(Media.file_size >= min_size)
            count_stmt = count_stmt.where(Media.file_size >= min_size)
        if max_size is not None:
            stmt = stmt.where(Media.file_size <= max_size)
            count_stmt = count_stmt.where(Media.file_size <= max_size)

        # Date range
        if uploaded_after:
            stmt = stmt.where(Media.uploaded_at >= uploaded_after)
            count_stmt = count_stmt.where(Media.uploaded_at >= uploaded_after)
        if uploaded_before:
            stmt = stmt.where(Media.uploaded_at <= uploaded_before)
            count_stmt = count_stmt.where(Media.uploaded_at <= uploaded_before)

        # Get total count
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        stmt = stmt.order_by(Media.uploaded_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)

        return list(result.scalars().all()), total

    @staticmethod
    async def get_all_media_admin(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0,
        file_type: str | None = None,
    ) -> tuple[list[Media], int]:
        """
        Get all media across all users (admin only).

        Returns:
            Tuple of (results, total_count)
        """
        stmt = select(Media)
        count_stmt = select(func.count(Media.id))

        if file_type:
            stmt = stmt.where(Media.file_type == file_type)
            count_stmt = count_stmt.where(Media.file_type == file_type)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(Media.uploaded_at.desc()).limit(limit).offset(offset)
        result = await db.execute(stmt)

        return list(result.scalars().all()), total

    @staticmethod
    async def bulk_delete_media(media_ids: list[int], current_user: User, db: AsyncSession) -> dict:
        """
        Delete multiple media files.

        Returns:
            Dict with success_count, failed_count, failed_items
        """
        from app.constants.roles import RoleEnum

        success_count = 0
        failed_items = []

        for media_id in media_ids:
            try:
                media = await UploadService.get_media_by_id(media_id, db)

                # Check permission
                if media.uploaded_by != current_user.id and current_user.role.name not in [
                    RoleEnum.ADMIN.value,
                    RoleEnum.SUPERADMIN.value,
                ]:
                    failed_items.append({"id": media_id, "error": "Not authorized"})
                    continue

                # Delete physical files
                UploadService._delete_media_files(media)

                await db.delete(media)
                success_count += 1

            except HTTPException:
                failed_items.append({"id": media_id, "error": "Media not found"})

        await db.commit()

        return {
            "success_count": success_count,
            "failed_count": len(failed_items),
            "failed_items": failed_items,
        }

    @staticmethod
    async def bulk_move_media(
        media_ids: list[int], folder_id: int | None, current_user: User, db: AsyncSession
    ) -> dict:
        """
        Move multiple media items to a folder.

        Returns:
            Dict with success_count, failed_count, failed_items
        """
        from app.constants.roles import RoleEnum

        # Validate folder if provided
        if folder_id is not None:
            from app.models.media_folder import MediaFolder

            folder_result = await db.execute(select(MediaFolder).where(MediaFolder.id == folder_id))
            folder = folder_result.scalars().first()
            if not folder:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
            if folder.user_id != current_user.id and current_user.role.name not in [
                RoleEnum.ADMIN.value,
                RoleEnum.SUPERADMIN.value,
            ]:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to use this folder")

        success_count = 0
        failed_items = []

        for media_id in media_ids:
            try:
                media = await UploadService.get_media_by_id(media_id, db)

                if media.uploaded_by != current_user.id and current_user.role.name not in [
                    RoleEnum.ADMIN.value,
                    RoleEnum.SUPERADMIN.value,
                ]:
                    failed_items.append({"id": media_id, "error": "Not authorized"})
                    continue

                media.folder_id = folder_id
                media.updated_at = datetime.now(timezone.utc)
                success_count += 1

            except HTTPException:
                failed_items.append({"id": media_id, "error": "Media not found"})

        await db.commit()

        return {
            "success_count": success_count,
            "failed_count": len(failed_items),
            "failed_items": failed_items,
        }

    @staticmethod
    def _delete_media_files(media: Media) -> None:
        """Delete all physical files associated with a media record."""
        try:
            file_path = Path(media.file_path)
            if file_path.exists():
                file_path.unlink()

            if media.thumbnail_path:
                thumbnail_path = Path(media.thumbnail_path)
                if thumbnail_path.exists():
                    thumbnail_path.unlink()

            # Delete size variants
            if media.sizes:
                for variant_path in media.sizes.values():
                    p = Path(variant_path)
                    if p.exists():
                        p.unlink()
        except Exception as e:
            logger.warning("Error deleting physical files for media %s: %s", media.id, e)

    @staticmethod
    async def delete_media(media_id: int, current_user: User, db: AsyncSession) -> None:
        """
        Delete media file and record.

        Args:
            media_id: Media ID
            current_user: User requesting deletion
            db: Database session

        Raises:
            HTTPException: If media not found or user not authorized
        """
        media = await UploadService.get_media_by_id(media_id, db)

        # Check if user owns the media (or is admin)
        from app.constants.roles import RoleEnum

        if media.uploaded_by != current_user.id and current_user.role.name not in [
            RoleEnum.ADMIN.value,
            RoleEnum.SUPERADMIN.value,
        ]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this media")

        # Delete physical files
        UploadService._delete_media_files(media)

        # Delete database record
        await db.delete(media)
        await db.commit()


# Singleton instance
upload_service = UploadService()
