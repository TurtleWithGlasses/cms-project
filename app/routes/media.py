"""
Media Routes

API endpoints for file upload and media management.
"""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.media import MediaListResponse, MediaResponse, MediaUploadResponse
from app.services.upload_service import UPLOAD_DIR, upload_service
from app.utils.security import validate_file_path

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")  # Rate limit: 10 uploads per hour per IP
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file (image or document).

    Supported image formats: JPEG, PNG, GIF, WebP
    Supported document formats: PDF, DOC, DOCX, XLS, XLSX, TXT, MD

    Maximum file size: 10MB
    Rate limit: 10 uploads per hour

    Returns the uploaded media information including URLs.
    """
    media = await upload_service.upload_file(file, current_user, db)

    # Generate URLs (in production, these would be full URLs)
    base_url = "/api/v1/media"

    return MediaUploadResponse(
        id=media.id,
        filename=media.filename,
        original_filename=media.original_filename,
        file_type=media.file_type,
        file_size=media.file_size,
        mime_type=media.mime_type,
        url=f"{base_url}/files/{media.id}",
        thumbnail_url=f"{base_url}/thumbnails/{media.id}" if media.thumbnail_path else None,
        width=media.width,
        height=media.height,
        uploaded_at=media.uploaded_at,
    )


@router.get("/", response_model=MediaListResponse)
async def list_media(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all media uploaded by the current user.

    - **limit**: Maximum number of results (default: 50, max: 100)
    - **offset**: Pagination offset
    """
    if limit > 100:
        limit = 100

    media_list = await upload_service.get_user_media(current_user.id, db, limit, offset)

    return MediaListResponse(
        media=media_list,
        total=len(media_list),
        limit=limit,
        offset=offset,
    )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get media information by ID.

    Returns metadata about the uploaded file.
    """
    media = await upload_service.get_media_by_id(media_id, db)

    # Check if user owns the media (or is admin)
    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this media")

    return media


@router.get("/files/{media_id}")
async def download_file(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Download/view the actual file.

    Returns the file with appropriate content type for inline viewing or download.
    """
    media = await upload_service.get_media_by_id(media_id, db)

    # Check authorization
    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file")

    # Validate file path to prevent path traversal attacks
    safe_file_path = validate_file_path(media.file_path, UPLOAD_DIR)

    if not safe_file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")

    return FileResponse(
        path=str(safe_file_path),
        media_type=media.mime_type,
        filename=media.original_filename,
    )


@router.get("/thumbnails/{media_id}")
async def get_thumbnail(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get thumbnail for an image.

    Only available for image files.
    """
    media = await upload_service.get_media_by_id(media_id, db)

    # Check authorization
    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file")

    if not media.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No thumbnail available for this media")

    # Validate thumbnail path to prevent path traversal attacks
    safe_thumbnail_path = validate_file_path(media.thumbnail_path, UPLOAD_DIR.parent)

    if not safe_thumbnail_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found on disk")

    return FileResponse(
        path=str(safe_thumbnail_path),
        media_type=media.mime_type,
    )


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a media file.

    Users can only delete their own files. Admins can delete any file.
    Deletes both the database record and the physical file.
    """
    await upload_service.delete_media(media_id, current_user, db)
    return None
