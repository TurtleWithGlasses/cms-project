"""
Media Folder Service

Handles CRUD operations for media folders.
"""

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media import Media
from app.models.media_folder import MediaFolder
from app.models.user import User


def _slugify(text: str) -> str:
    """Generate a URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


class MediaFolderService:
    """Service for managing media folders."""

    @staticmethod
    async def create_folder(name: str, parent_id: int | None, current_user: User, db: AsyncSession) -> MediaFolder:
        """Create a new media folder."""
        # Validate parent folder if provided
        if parent_id is not None:
            parent_result = await db.execute(
                select(MediaFolder).where(
                    MediaFolder.id == parent_id,
                    MediaFolder.user_id == current_user.id,
                )
            )
            parent = parent_result.scalars().first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent folder not found",
                )

        folder = MediaFolder(
            name=name,
            slug=_slugify(name),
            parent_id=parent_id,
            user_id=current_user.id,
        )

        db.add(folder)
        await db.commit()
        await db.refresh(folder)

        return folder

    @staticmethod
    async def get_user_folders(user_id: int, db: AsyncSession) -> list[MediaFolder]:
        """Get all folders for a user."""
        result = await db.execute(select(MediaFolder).where(MediaFolder.user_id == user_id).order_by(MediaFolder.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_folder_by_id(folder_id: int, current_user: User, db: AsyncSession) -> MediaFolder:
        """Get a folder by ID, verifying ownership."""
        from app.constants.roles import RoleEnum

        result = await db.execute(select(MediaFolder).where(MediaFolder.id == folder_id))
        folder = result.scalars().first()

        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )

        if folder.user_id != current_user.id and current_user.role.name not in [
            RoleEnum.ADMIN.value,
            RoleEnum.SUPERADMIN.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this folder",
            )

        return folder

    @staticmethod
    async def update_folder(folder_id: int, name: str, current_user: User, db: AsyncSession) -> MediaFolder:
        """Update a folder name."""
        folder = await MediaFolderService.get_folder_by_id(folder_id, current_user, db)

        folder.name = name
        folder.slug = _slugify(name)

        await db.commit()
        await db.refresh(folder)

        return folder

    @staticmethod
    async def delete_folder(folder_id: int, current_user: User, db: AsyncSession) -> None:
        """Delete a folder. Media items are moved to root (folder_id=None)."""
        folder = await MediaFolderService.get_folder_by_id(folder_id, current_user, db)

        # Move contained media to root
        media_result = await db.execute(select(Media).where(Media.folder_id == folder_id))
        for media_item in media_result.scalars().all():
            media_item.folder_id = folder.parent_id

        # Move subfolders to parent
        subfolder_result = await db.execute(select(MediaFolder).where(MediaFolder.parent_id == folder_id))
        for subfolder in subfolder_result.scalars().all():
            subfolder.parent_id = folder.parent_id

        await db.delete(folder)
        await db.commit()


media_folder_service = MediaFolderService()
