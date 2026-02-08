"""
Media Routes

API endpoints for file upload and media management.
"""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.database import get_db
from app.middleware.rate_limit import limiter
from app.models.user import User
from app.schemas.media import (
    BulkMediaDeleteRequest,
    BulkMediaMoveRequest,
    BulkOperationResponse,
    MediaListResponse,
    MediaResponse,
    MediaUpdateRequest,
    MediaUploadResponse,
)
from app.services.upload_service import IMAGE_SIZES, UPLOAD_DIR, upload_service
from app.utils.security import validate_file_path

router = APIRouter(tags=["Media"])


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
    """
    media = await upload_service.upload_file(file, current_user, db)

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
        alt_text=media.alt_text,
        title=media.title,
        tags=media.tags or [],
        sizes={name: f"{base_url}/sizes/{media.id}/{name}" for name in (media.sizes or {})},
        uploaded_at=media.uploaded_at,
    )


@router.post("/bulk-upload", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def bulk_upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload multiple files at once (max 10).

    Rate limit: 5 bulk uploads per hour
    """
    if len(files) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 10 files per bulk upload")

    base_url = "/api/v1/media"
    success_items = []
    failed_items = []

    for file in files:
        try:
            media = await upload_service.upload_file(file, current_user, db)
            success_items.append(
                MediaUploadResponse(
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
                    alt_text=media.alt_text,
                    title=media.title,
                    tags=media.tags or [],
                    sizes={name: f"{base_url}/sizes/{media.id}/{name}" for name in (media.sizes or {})},
                    uploaded_at=media.uploaded_at,
                )
            )
        except HTTPException as e:
            failed_items.append({"filename": file.filename or "unknown", "error": e.detail})

    return {
        "success_count": len(success_items),
        "failed_count": len(failed_items),
        "success_items": [item.model_dump() for item in success_items],
        "failed_items": failed_items,
    }


@router.get("/search", response_model=MediaListResponse)
async def search_media(
    query: Annotated[str | None, Query(description="Search in filename, alt_text, title")] = None,
    file_type: Annotated[str | None, Query(description="Filter by file_type")] = None,
    folder_id: Annotated[int | None, Query(description="Filter by folder")] = None,
    tags: Annotated[str | None, Query(description="Comma-separated tags")] = None,
    min_size: Annotated[int | None, Query(description="Min file size in bytes")] = None,
    max_size: Annotated[int | None, Query(description="Max file size in bytes")] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search and filter media files."""
    if limit > 100:
        limit = 100

    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else None

    results, total = await upload_service.search_media(
        user_id=current_user.id,
        db=db,
        query=query,
        file_type=file_type,
        folder_id=folder_id,
        tags=tag_list,
        min_size=min_size,
        max_size=max_size,
        limit=limit,
        offset=offset,
    )

    return MediaListResponse(media=results, total=total, limit=limit, offset=offset)


@router.get("/admin/all", response_model=MediaListResponse)
async def admin_list_all_media(
    limit: int = 50,
    offset: int = 0,
    file_type: str | None = None,
    current_user: User = Depends(require_role(["admin", "superadmin"])),
    db: AsyncSession = Depends(get_db),
):
    """List all media across all users (admin only)."""
    if limit > 100:
        limit = 100

    results, total = await upload_service.get_all_media_admin(db, limit, offset, file_type)
    return MediaListResponse(media=results, total=total, limit=limit, offset=offset)


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
    """Get media information by ID."""
    media = await upload_service.get_media_by_id(media_id, db)

    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this media")

    return media


@router.patch("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: int,
    update_data: MediaUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update media metadata (alt_text, title, description, tags, folder)."""
    updates = update_data.model_dump(exclude_unset=True)
    media = await upload_service.update_media(media_id, updates, current_user, db)
    return media


@router.get("/files/{media_id}")
async def download_file(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download/view the actual file."""
    media = await upload_service.get_media_by_id(media_id, db)

    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file")

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
    """Get thumbnail for an image."""
    media = await upload_service.get_media_by_id(media_id, db)

    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file")

    if not media.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No thumbnail available for this media")

    safe_thumbnail_path = validate_file_path(media.thumbnail_path, UPLOAD_DIR.parent)

    if not safe_thumbnail_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found on disk")

    return FileResponse(
        path=str(safe_thumbnail_path),
        media_type=media.mime_type,
    )


@router.get("/sizes/{media_id}/{size}")
async def get_image_size(
    media_id: int,
    size: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific image size variant (small, medium, large)."""
    if size not in IMAGE_SIZES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid size. Must be one of: {', '.join(IMAGE_SIZES.keys())}",
        )

    media = await upload_service.get_media_by_id(media_id, db)

    from app.constants.roles import RoleEnum

    if media.uploaded_by != current_user.id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this file")

    if not media.sizes or size not in media.sizes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Size variant '{size}' not available")

    variant_path = Path(media.sizes[size])
    if not variant_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Size variant file not found on disk")

    return FileResponse(
        path=str(variant_path),
        media_type=media.mime_type,
    )


@router.post("/bulk-delete", response_model=BulkOperationResponse)
async def bulk_delete_media(
    request_data: BulkMediaDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple media files at once."""
    result = await upload_service.bulk_delete_media(request_data.media_ids, current_user, db)
    return BulkOperationResponse(**result)


@router.post("/bulk-move", response_model=BulkOperationResponse)
async def bulk_move_media(
    request_data: BulkMediaMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move multiple media files to a folder."""
    result = await upload_service.bulk_move_media(request_data.media_ids, request_data.folder_id, current_user, db)
    return BulkOperationResponse(**result)


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
