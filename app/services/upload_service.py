"""
Upload Service

Handles file uploads, validation, image processing, and storage.
"""

import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.user import User

# Configuration
UPLOAD_DIR = Path("uploads")
THUMBNAIL_DIR = UPLOAD_DIR / "thumbnails"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
THUMBNAIL_SIZE = (300, 300)

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
            with open(file_path, "wb") as buffer:
                while chunk := await file.read(8192):
                    file_size += len(chunk)

                    # Check file size limit
                    if file_size > MAX_FILE_SIZE:
                        # Clean up partial file
                        buffer.close()
                        os.remove(file_path)
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
                os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {str(e)}"
            )

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
            print(f"Failed to create thumbnail: {e}")
            return None, None, None

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

        # Process image (create thumbnail and get dimensions)
        thumbnail_path = None
        width = None
        height = None

        if file_type == "image":
            thumbnail_filename = f"thumb_{unique_filename}"
            thumbnail_path, width, height = self.create_thumbnail(file_path, thumbnail_filename)

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
        from sqlalchemy.future import select

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
        from sqlalchemy.future import select

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
            RoleEnum.admin.value,
            RoleEnum.superadmin.value,
        ]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this media")

        # Delete physical files
        try:
            file_path = Path(media.file_path)
            if file_path.exists():
                os.remove(file_path)

            if media.thumbnail_path:
                thumbnail_path = Path(media.thumbnail_path)
                if thumbnail_path.exists():
                    os.remove(thumbnail_path)
        except Exception as e:
            print(f"Error deleting physical files: {e}")

        # Delete database record
        await db.delete(media)
        await db.commit()


# Singleton instance
upload_service = UploadService()
