"""Import routes for importing content and users from various formats."""

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.import_job import DuplicateHandling, ImportFormat, ImportStatus
from app.models.user import User
from app.routes.auth import get_current_user, require_role
from app.services import import_service

router = APIRouter(tags=["Import"])


# Pydantic schemas
class ImportJobResponse(BaseModel):
    """Schema for import job response."""

    id: int
    name: str
    description: str | None
    import_type: str
    import_format: str
    status: str
    duplicate_handling: str
    file_name: str
    file_size: int | None
    total_records: int
    processed_records: int
    successful_records: int
    failed_records: int
    skipped_records: int
    created_at: str
    started_at: str | None
    completed_at: str | None

    model_config = {"from_attributes": True}


class ImportRecordResponse(BaseModel):
    """Schema for import record response."""

    id: int
    row_number: int
    source_id: str | None
    status: str
    created_record_id: int | None
    created_record_type: str | None
    error_message: str | None
    processed_at: str | None

    model_config = {"from_attributes": True}


class ImportResultsResponse(BaseModel):
    """Schema for import results summary."""

    job: ImportJobResponse
    summary: dict | None
    errors: list[dict] | None


# Routes
@router.post("/content/json", response_model=ImportJobResponse)
async def import_content_json(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    field_mapping: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import content from JSON file."""
    mapping = json.loads(field_mapping) if field_mapping else None
    job = await import_service.import_content(
        db=db,
        file=file,
        import_format=ImportFormat.JSON,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
        field_mapping=mapping,
    )
    return _job_to_response(job)


@router.post("/content/csv", response_model=ImportJobResponse)
async def import_content_csv(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    field_mapping: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import content from CSV file."""
    mapping = json.loads(field_mapping) if field_mapping else None
    job = await import_service.import_content(
        db=db,
        file=file,
        import_format=ImportFormat.CSV,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
        field_mapping=mapping,
    )
    return _job_to_response(job)


@router.post("/content/xml", response_model=ImportJobResponse)
async def import_content_xml(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    field_mapping: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import content from XML file."""
    mapping = json.loads(field_mapping) if field_mapping else None
    job = await import_service.import_content(
        db=db,
        file=file,
        import_format=ImportFormat.XML,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
        field_mapping=mapping,
    )
    return _job_to_response(job)


@router.post("/content/wordpress", response_model=ImportJobResponse)
async def import_content_wordpress(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import content from a WordPress eXtended RSS (WXR) XML export file."""
    job = await import_service.import_content_wordpress(
        db=db,
        file=file,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
    )
    return _job_to_response(job)


@router.post("/content/markdown", response_model=ImportJobResponse)
async def import_content_markdown(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import a single Markdown file with YAML frontmatter as a content item."""
    job = await import_service.import_content_markdown(
        db=db,
        file=file,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
    )
    return _job_to_response(job)


@router.post("/users/csv", response_model=ImportJobResponse)
async def import_users_csv(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    field_mapping: str | None = Form(None),
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Import users from CSV file. Admin only."""
    mapping = json.loads(field_mapping) if field_mapping else None
    job = await import_service.import_users(
        db=db,
        file=file,
        import_format=ImportFormat.CSV,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
        field_mapping=mapping,
    )
    return _job_to_response(job)


@router.post("/users/json", response_model=ImportJobResponse)
async def import_users_json(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    duplicate_handling: DuplicateHandling = Form(DuplicateHandling.SKIP),
    field_mapping: str | None = Form(None),
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Import users from JSON file. Admin only."""
    mapping = json.loads(field_mapping) if field_mapping else None
    job = await import_service.import_users(
        db=db,
        file=file,
        import_format=ImportFormat.JSON,
        user_id=current_user.id,
        name=name,
        duplicate_handling=duplicate_handling,
        field_mapping=mapping,
    )
    return _job_to_response(job)


@router.get("/jobs", response_model=list[ImportJobResponse])
async def get_import_jobs(
    status_filter: ImportStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get import jobs for the current user."""
    jobs = await import_service.get_import_jobs(
        db=db,
        user_id=current_user.id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    return [_job_to_response(job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=ImportResultsResponse)
async def get_import_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get import job details with results."""
    job = await import_service.get_import_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    if job.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job",
        )

    return ImportResultsResponse(
        job=_job_to_response(job),
        summary=json.loads(job.results_summary) if job.results_summary else None,
        errors=json.loads(job.error_log) if job.error_log else None,
    )


@router.get("/jobs/{job_id}/records", response_model=list[ImportRecordResponse])
async def get_import_records(
    job_id: int,
    status_filter: ImportStatus | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get individual records for an import job."""
    job = await import_service.get_import_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    if job.created_by_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job",
        )

    records = await import_service.get_import_records(
        db=db,
        job_id=job_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )

    return [
        ImportRecordResponse(
            id=r.id,
            row_number=r.row_number,
            source_id=r.source_id,
            status=r.status.value,
            created_record_id=r.created_record_id,
            created_record_type=r.created_record_type,
            error_message=r.error_message,
            processed_at=r.processed_at.isoformat() if r.processed_at else None,
        )
        for r in records
    ]


@router.post("/jobs/{job_id}/cancel", response_model=ImportJobResponse)
async def cancel_import_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or processing import job."""
    job = await import_service.cancel_import_job(db, job_id, current_user.id)
    return _job_to_response(job)


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported import formats."""
    return {
        "formats": [f.value for f in ImportFormat],
        "duplicate_handling_options": [d.value for d in DuplicateHandling],
        "content_fields": [
            "title",
            "slug",
            "body",
            "excerpt",
            "status",
            "category",
            "tags",
        ],
        "user_fields": [
            "email",
            "username",
            "full_name",
            "is_active",
        ],
    }


def _job_to_response(job) -> ImportJobResponse:
    """Convert import job to response schema."""
    return ImportJobResponse(
        id=job.id,
        name=job.name,
        description=job.description,
        import_type=job.import_type.value,
        import_format=job.import_format.value,
        status=job.status.value,
        duplicate_handling=job.duplicate_handling.value,
        file_name=job.file_name,
        file_size=job.file_size,
        total_records=job.total_records,
        processed_records=job.processed_records,
        successful_records=job.successful_records,
        failed_records=job.failed_records,
        skipped_records=job.skipped_records,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
