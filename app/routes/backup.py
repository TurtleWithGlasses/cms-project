"""
Backup Routes

API endpoints for database backup management.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db
from app.models.backup import BackupStatus, BackupType
from app.models.user import User
from app.services.backup_service import BackupService

router = APIRouter(tags=["Backups"])


# =============================================================================
# Schemas
# =============================================================================


class BackupCreateRequest(BaseModel):
    """Request to create a new backup."""

    backup_type: str = Field(default="full", description="Type of backup: full, incremental, content_only, media_only")
    include_database: bool = Field(default=True, description="Include database dump")
    include_media: bool = Field(default=True, description="Include media files")
    include_config: bool = Field(default=False, description="Include configuration files")
    description: str | None = Field(None, max_length=500, description="Optional description")


class BackupResponse(BaseModel):
    """Response for a backup."""

    id: int
    filename: str
    file_size: int | None
    file_size_mb: float | None
    backup_type: str
    status: str
    description: str | None
    include_database: bool
    include_media: bool
    include_config: bool
    created_at: str
    started_at: str | None
    completed_at: str | None
    duration_seconds: float | None
    error_message: str | None

    class Config:
        from_attributes = True


class BackupListResponse(BaseModel):
    """Response for listing backups."""

    backups: list[BackupResponse]
    total: int
    limit: int
    offset: int


class BackupScheduleRequest(BaseModel):
    """Request to update backup schedule."""

    enabled: bool | None = None
    frequency: str | None = Field(None, description="daily, weekly, or monthly")
    time_of_day: str | None = Field(None, description="Time in HH:MM format")
    day_of_week: int | None = Field(None, ge=0, le=6, description="0=Monday, 6=Sunday")
    day_of_month: int | None = Field(None, ge=1, le=31)
    retention_days: int | None = Field(None, ge=1, le=365)
    max_backups: int | None = Field(None, ge=1, le=100)
    backup_type: str | None = None
    include_database: bool | None = None
    include_media: bool | None = None
    include_config: bool | None = None


class BackupScheduleResponse(BaseModel):
    """Response for backup schedule."""

    id: int
    enabled: bool
    frequency: str
    time_of_day: str
    day_of_week: int | None
    day_of_month: int | None
    retention_days: int
    max_backups: int
    backup_type: str
    include_database: bool
    include_media: bool
    include_config: bool
    last_run_at: str | None
    next_run_at: str | None

    class Config:
        from_attributes = True


class StorageInfoResponse(BaseModel):
    """Response for storage information."""

    backup_count: int
    total_size_bytes: int
    total_size_mb: float
    backup_directory: str
    disk_total_bytes: int
    disk_free_bytes: int
    disk_used_percent: float


# =============================================================================
# Helper Functions
# =============================================================================


def _backup_to_response(backup) -> BackupResponse:
    """Convert backup model to response schema."""
    return BackupResponse(
        id=backup.id,
        filename=backup.filename,
        file_size=backup.file_size,
        file_size_mb=backup.file_size_mb,
        backup_type=backup.backup_type.value,
        status=backup.status.value,
        description=backup.description,
        include_database=backup.include_database,
        include_media=backup.include_media,
        include_config=backup.include_config,
        created_at=backup.created_at.isoformat() if backup.created_at else None,
        started_at=backup.started_at.isoformat() if backup.started_at else None,
        completed_at=backup.completed_at.isoformat() if backup.completed_at else None,
        duration_seconds=backup.duration_seconds,
        error_message=backup.error_message,
    )


def _schedule_to_response(schedule) -> BackupScheduleResponse:
    """Convert schedule model to response schema."""
    return BackupScheduleResponse(
        id=schedule.id,
        enabled=schedule.enabled,
        frequency=schedule.frequency,
        time_of_day=schedule.time_of_day,
        day_of_week=schedule.day_of_week,
        day_of_month=schedule.day_of_month,
        retention_days=schedule.retention_days,
        max_backups=schedule.max_backups,
        backup_type=schedule.backup_type.value,
        include_database=schedule.include_database,
        include_media=schedule.include_media,
        include_config=schedule.include_config,
        last_run_at=schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        next_run_at=schedule.next_run_at.isoformat() if schedule.next_run_at else None,
    )


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=BackupListResponse)
async def list_backups(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    List all backups.

    Requires admin or superadmin role.
    """
    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = BackupStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: {[s.value for s in BackupStatus]}",
            ) from None

    service = BackupService(db)
    backups, total = await service.list_backups(limit=limit, offset=offset, status=status_enum)

    return BackupListResponse(
        backups=[_backup_to_response(b) for b in backups],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=BackupResponse, status_code=status.HTTP_201_CREATED)
async def create_backup(
    request: BackupCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Create a new backup.

    Requires admin or superadmin role.
    """
    # Convert backup type string to enum
    try:
        backup_type = BackupType(request.backup_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid backup type: {request.backup_type}. Valid values: {[t.value for t in BackupType]}",
        ) from None

    service = BackupService(db)
    backup = await service.create_backup(
        backup_type=backup_type,
        include_database=request.include_database,
        include_media=request.include_media,
        include_config=request.include_config,
        description=request.description,
        created_by_id=current_user.id,
    )

    return _backup_to_response(backup)


@router.get("/{backup_id}", response_model=BackupResponse)
async def get_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Get a specific backup by ID.

    Requires admin or superadmin role.
    """
    service = BackupService(db)
    backup = await service.get_backup(backup_id)

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup with ID {backup_id} not found",
        )

    return _backup_to_response(backup)


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Delete a backup.

    Requires admin or superadmin role.
    """
    service = BackupService(db)
    deleted = await service.delete_backup(backup_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup with ID {backup_id} not found",
        )


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Download a backup file.

    Requires admin or superadmin role.
    """
    service = BackupService(db)
    backup = await service.get_backup(backup_id)

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup with ID {backup_id} not found",
        )

    if backup.status != BackupStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot download backup with status {backup.status.value}",
        )

    if not backup.file_path or not Path(backup.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk",
        )

    return FileResponse(
        path=backup.file_path,
        filename=backup.filename,
        media_type="application/gzip",
    )


@router.post("/{backup_id}/restore", status_code=status.HTTP_200_OK)
async def restore_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["superadmin"])),
):
    """
    Restore from a backup.

    WARNING: This is a destructive operation.
    Requires superadmin role.
    """
    service = BackupService(db)

    try:
        await service.restore_backup(backup_id)
        return {"message": "Restore initiated successfully", "backup_id": backup_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from None


@router.get("/schedule", response_model=BackupScheduleResponse | None)
async def get_schedule(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Get the current backup schedule.

    Requires admin or superadmin role.
    """
    service = BackupService(db)
    schedule = await service.get_schedule()

    if not schedule:
        # Return default schedule
        return BackupScheduleResponse(
            id=0,
            enabled=False,
            frequency="daily",
            time_of_day="02:00",
            day_of_week=None,
            day_of_month=None,
            retention_days=30,
            max_backups=10,
            backup_type="full",
            include_database=True,
            include_media=True,
            include_config=False,
            last_run_at=None,
            next_run_at=None,
        )

    return _schedule_to_response(schedule)


@router.put("/schedule", response_model=BackupScheduleResponse)
async def update_schedule(
    request: BackupScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Update the backup schedule.

    Requires admin or superadmin role.
    """
    # Convert backup type if provided
    backup_type = None
    if request.backup_type:
        try:
            backup_type = BackupType(request.backup_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid backup type: {request.backup_type}",
            ) from None

    service = BackupService(db)
    schedule = await service.update_schedule(
        enabled=request.enabled,
        frequency=request.frequency,
        time_of_day=request.time_of_day,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        retention_days=request.retention_days,
        max_backups=request.max_backups,
        backup_type=backup_type,
        include_database=request.include_database,
        include_media=request.include_media,
        include_config=request.include_config,
    )

    return _schedule_to_response(schedule)


@router.get("/storage", response_model=StorageInfoResponse)
async def get_storage_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "superadmin"])),
):
    """
    Get backup storage information.

    Requires admin or superadmin role.
    """
    service = BackupService(db)
    info = await service.get_storage_info()

    return StorageInfoResponse(**info)
