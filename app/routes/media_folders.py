"""
Media Folder Routes

API endpoints for managing media folders.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.media import (
    MediaFolderCreate,
    MediaFolderListResponse,
    MediaFolderResponse,
    MediaFolderUpdate,
    MediaListResponse,
)
from app.services.media_folder_service import media_folder_service
from app.services.upload_service import upload_service

router = APIRouter(tags=["Media Folders"])


@router.post("/", response_model=MediaFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: MediaFolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new media folder."""
    folder = await media_folder_service.create_folder(data.name, data.parent_id, current_user, db)
    return folder


@router.get("/", response_model=MediaFolderListResponse)
async def list_folders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all folders for the current user."""
    folders = await media_folder_service.get_user_folders(current_user.id, db)
    return MediaFolderListResponse(folders=folders)


@router.get("/{folder_id}", response_model=MediaFolderResponse)
async def get_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get folder details by ID."""
    return await media_folder_service.get_folder_by_id(folder_id, current_user, db)


@router.get("/{folder_id}/media", response_model=MediaListResponse)
async def get_folder_media(
    folder_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List media items in a specific folder."""
    # Verify folder access
    await media_folder_service.get_folder_by_id(folder_id, current_user, db)

    if limit > 100:
        limit = 100

    results, total = await upload_service.search_media(
        user_id=current_user.id,
        db=db,
        folder_id=folder_id,
        limit=limit,
        offset=offset,
    )

    return MediaListResponse(media=results, total=total, limit=limit, offset=offset)


@router.patch("/{folder_id}", response_model=MediaFolderResponse)
async def update_folder(
    folder_id: int,
    data: MediaFolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename a folder."""
    return await media_folder_service.update_folder(folder_id, data.name, current_user, db)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a folder.

    Media items in the folder are moved to the parent folder (or root).
    Subfolders are also moved to the parent folder.
    """
    await media_folder_service.delete_folder(folder_id, current_user, db)
    return None
