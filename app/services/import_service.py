"""Content import service for importing data from various formats."""

import csv
import io
import json
from datetime import datetime

import defusedxml.ElementTree as DefusedET  # Secure XML parsing
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.content import Content
from app.models.import_job import (
    DuplicateHandling,
    ImportFormat,
    ImportJob,
    ImportRecord,
    ImportStatus,
    ImportType,
)
from app.models.tag import Tag
from app.models.user import User


async def create_import_job(
    db: AsyncSession,
    name: str,
    import_type: ImportType,
    import_format: ImportFormat,
    file_name: str,
    created_by_id: int,
    description: str | None = None,
    duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP,
    field_mapping: dict | None = None,
) -> ImportJob:
    """Create a new import job."""
    job = ImportJob(
        name=name,
        description=description,
        import_type=import_type,
        import_format=import_format,
        file_name=file_name,
        duplicate_handling=duplicate_handling,
        field_mapping=json.dumps(field_mapping) if field_mapping else None,
        created_by_id=created_by_id,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_import_job(db: AsyncSession, job_id: int) -> ImportJob | None:
    """Get import job by ID."""
    result = await db.execute(
        select(ImportJob).options(selectinload(ImportJob.created_by)).where(ImportJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def get_import_jobs(
    db: AsyncSession,
    user_id: int | None = None,
    status_filter: ImportStatus | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[ImportJob]:
    """Get import jobs with optional filters."""
    query = select(ImportJob).order_by(ImportJob.created_at.desc())

    if user_id:
        query = query.where(ImportJob.created_by_id == user_id)
    if status_filter:
        query = query.where(ImportJob.status == status_filter)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_job_status(
    db: AsyncSession,
    job_id: int,
    status_value: ImportStatus,
    error_log: list | None = None,
    results_summary: dict | None = None,
) -> ImportJob:
    """Update import job status."""
    job = await get_import_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    job.status = status_value

    if status_value == ImportStatus.PROCESSING and not job.started_at:
        job.started_at = datetime.utcnow()
    elif status_value in [
        ImportStatus.COMPLETED,
        ImportStatus.FAILED,
        ImportStatus.PARTIAL,
    ]:
        job.completed_at = datetime.utcnow()

    if error_log:
        job.error_log = json.dumps(error_log)
    if results_summary:
        job.results_summary = json.dumps(results_summary)

    await db.commit()
    await db.refresh(job)
    return job


async def parse_json_content(file_content: bytes) -> list[dict]:
    """Parse JSON content file."""
    try:
        data = json.loads(file_content.decode("utf-8"))
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "items" in data:
            return data["items"]
        elif isinstance(data, dict):
            return [data]
        return []
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format: {e!s}",
        ) from e


async def parse_csv_content(file_content: bytes) -> list[dict]:
    """Parse CSV content file."""
    try:
        text = file_content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {e!s}",
        ) from e


async def parse_xml_content(file_content: bytes) -> list[dict]:
    """Parse XML content file."""
    try:
        root = DefusedET.fromstring(file_content.decode("utf-8"))
        items = []

        # Look for content items (support various XML structures)
        for item in root.findall(".//item") or root.findall(".//content"):
            item_dict = {}
            for child in item:
                item_dict[child.tag] = child.text
            items.append(item_dict)

        if not items:
            # Try treating each child as an item
            for child in root:
                item_dict = {}
                for grandchild in child:
                    item_dict[grandchild.tag] = grandchild.text
                if item_dict:
                    items.append(item_dict)

        return items
    except DefusedET.ParseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid XML format: {e!s}",
        ) from e


async def apply_field_mapping(data: dict, field_mapping: dict | None) -> dict:
    """Apply field mapping to transform source fields to destination fields."""
    if not field_mapping:
        return data

    mapped = {}
    for source_field, dest_field in field_mapping.items():
        if source_field in data:
            mapped[dest_field] = data[source_field]

    # Include unmapped fields
    for key, value in data.items():
        if key not in field_mapping and key not in mapped:
            mapped[key] = value

    return mapped


async def validate_content_record(data: dict) -> tuple[bool, str | None]:
    """Validate a content record."""
    required_fields = ["title"]

    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Missing required field: {field}"

    return True, None


async def find_duplicate_content(db: AsyncSession, title: str, slug: str | None = None) -> Content | None:
    """Find existing content by title or slug."""
    query = select(Content).where(Content.title == title)
    if slug:
        query = query.where(Content.slug == slug)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none()


async def process_content_import(
    db: AsyncSession,
    job: ImportJob,
    records: list[dict],
    author_id: int,
) -> ImportJob:
    """Process content import job."""
    job.total_records = len(records)
    job.status = ImportStatus.PROCESSING
    job.started_at = datetime.utcnow()
    await db.commit()

    field_mapping = json.loads(job.field_mapping) if job.field_mapping else None
    errors = []

    for idx, record in enumerate(records):
        row_num = idx + 1
        import_record = ImportRecord(
            import_job_id=job.id,
            row_number=row_num,
            source_data=json.dumps(record),
        )
        db.add(import_record)

        try:
            # Apply field mapping
            mapped_data = await apply_field_mapping(record, field_mapping)

            # Validate record
            is_valid, error_msg = await validate_content_record(mapped_data)
            if not is_valid:
                import_record.status = ImportStatus.FAILED
                import_record.error_message = error_msg
                job.failed_records += 1
                errors.append({"row": row_num, "error": error_msg})
                continue

            # Check for duplicates
            existing = await find_duplicate_content(db, mapped_data["title"], mapped_data.get("slug"))

            if existing:
                if job.duplicate_handling == DuplicateHandling.SKIP:
                    import_record.status = ImportStatus.COMPLETED
                    job.skipped_records += 1
                    continue
                elif job.duplicate_handling == DuplicateHandling.UPDATE:
                    # Update existing content
                    for key in ["title", "body", "excerpt", "status"]:
                        if key in mapped_data:
                            setattr(existing, key, mapped_data[key])
                    import_record.created_record_id = existing.id
                    import_record.created_record_type = "content"
                    import_record.status = ImportStatus.COMPLETED
                    job.successful_records += 1
                    continue
                elif job.duplicate_handling == DuplicateHandling.FAIL:
                    import_record.status = ImportStatus.FAILED
                    import_record.error_message = "Duplicate content found"
                    job.failed_records += 1
                    errors.append({"row": row_num, "error": "Duplicate content"})
                    continue

            # Create new content
            content = Content(
                title=mapped_data["title"],
                slug=mapped_data.get("slug"),
                body=mapped_data.get("body", ""),
                excerpt=mapped_data.get("excerpt"),
                status=mapped_data.get("status", "draft"),
                author_id=author_id,
            )

            # Handle category
            if "category" in mapped_data:
                cat_result = await db.execute(select(Category).where(Category.name == mapped_data["category"]))
                category = cat_result.scalar_one_or_none()
                if category:
                    content.category_id = category.id

            db.add(content)
            await db.flush()

            # Handle tags
            if "tags" in mapped_data:
                tag_names = (
                    mapped_data["tags"].split(",") if isinstance(mapped_data["tags"], str) else mapped_data["tags"]
                )
                for tag_name in tag_names:
                    tag_name = tag_name.strip()
                    if tag_name:
                        tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
                        tag = tag_result.scalar_one_or_none()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.add(tag)
                            await db.flush()
                        content.tags.append(tag)

            import_record.created_record_id = content.id
            import_record.created_record_type = "content"
            import_record.status = ImportStatus.COMPLETED
            job.successful_records += 1

        except Exception as e:
            import_record.status = ImportStatus.FAILED
            import_record.error_message = str(e)
            job.failed_records += 1
            errors.append({"row": row_num, "error": str(e)})

        import_record.processed_at = datetime.utcnow()
        job.processed_records += 1

    # Update job status
    if job.failed_records == 0:
        job.status = ImportStatus.COMPLETED
    elif job.successful_records > 0:
        job.status = ImportStatus.PARTIAL
    else:
        job.status = ImportStatus.FAILED

    job.completed_at = datetime.utcnow()
    job.error_log = json.dumps(errors) if errors else None
    job.results_summary = json.dumps(
        {
            "total": job.total_records,
            "successful": job.successful_records,
            "failed": job.failed_records,
            "skipped": job.skipped_records,
        }
    )

    await db.commit()
    await db.refresh(job)
    return job


async def process_user_import(
    db: AsyncSession,
    job: ImportJob,
    records: list[dict],
) -> ImportJob:
    """Process user import job."""
    job.total_records = len(records)
    job.status = ImportStatus.PROCESSING
    job.started_at = datetime.utcnow()
    await db.commit()

    field_mapping = json.loads(job.field_mapping) if job.field_mapping else None
    errors = []

    for idx, record in enumerate(records):
        row_num = idx + 1
        import_record = ImportRecord(
            import_job_id=job.id,
            row_number=row_num,
            source_data=json.dumps(record),
        )
        db.add(import_record)

        try:
            mapped_data = await apply_field_mapping(record, field_mapping)

            # Validate required fields
            if "email" not in mapped_data:
                import_record.status = ImportStatus.FAILED
                import_record.error_message = "Missing required field: email"
                job.failed_records += 1
                errors.append({"row": row_num, "error": "Missing email"})
                continue

            # Check for existing user
            result = await db.execute(select(User).where(User.email == mapped_data["email"]))
            existing = result.scalar_one_or_none()

            if existing:
                if job.duplicate_handling == DuplicateHandling.SKIP:
                    import_record.status = ImportStatus.COMPLETED
                    job.skipped_records += 1
                    continue
                elif job.duplicate_handling == DuplicateHandling.UPDATE:
                    for key in ["username", "full_name", "is_active"]:
                        if key in mapped_data:
                            setattr(existing, key, mapped_data[key])
                    import_record.created_record_id = existing.id
                    import_record.created_record_type = "user"
                    import_record.status = ImportStatus.COMPLETED
                    job.successful_records += 1
                    continue
                elif job.duplicate_handling == DuplicateHandling.FAIL:
                    import_record.status = ImportStatus.FAILED
                    import_record.error_message = "Duplicate user found"
                    job.failed_records += 1
                    errors.append({"row": row_num, "error": "Duplicate user"})
                    continue

            # Create new user (with random password that must be reset)
            import secrets

            user = User(
                email=mapped_data["email"],
                username=mapped_data.get("username", mapped_data["email"].split("@")[0]),
                full_name=mapped_data.get("full_name", ""),
                hashed_password=secrets.token_urlsafe(32),  # Temporary
                is_active=mapped_data.get("is_active", True),
            )
            db.add(user)
            await db.flush()

            import_record.created_record_id = user.id
            import_record.created_record_type = "user"
            import_record.status = ImportStatus.COMPLETED
            job.successful_records += 1

        except Exception as e:
            import_record.status = ImportStatus.FAILED
            import_record.error_message = str(e)
            job.failed_records += 1
            errors.append({"row": row_num, "error": str(e)})

        import_record.processed_at = datetime.utcnow()
        job.processed_records += 1

    # Update job status
    if job.failed_records == 0:
        job.status = ImportStatus.COMPLETED
    elif job.successful_records > 0:
        job.status = ImportStatus.PARTIAL
    else:
        job.status = ImportStatus.FAILED

    job.completed_at = datetime.utcnow()
    job.error_log = json.dumps(errors) if errors else None
    job.results_summary = json.dumps(
        {
            "total": job.total_records,
            "successful": job.successful_records,
            "failed": job.failed_records,
            "skipped": job.skipped_records,
        }
    )

    await db.commit()
    await db.refresh(job)
    return job


# WordPress namespace constants
_WP_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_WP_DC_NS = "http://purl.org/dc/elements/1.1/"
_WP_NS = "http://wordpress.org/export/1.2/"

# WordPress → CMS status mapping
_WP_STATUS_MAP = {
    "publish": "published",
    "draft": "draft",
    "pending": "pending",
    "private": "draft",
    "future": "pending",
}


async def parse_wordpress_xml(file_content: bytes) -> list[dict]:
    """Parse WordPress eXtended RSS (WXR) format and return content records."""
    try:
        root = DefusedET.fromstring(file_content.decode("utf-8"))
    except DefusedET.ParseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid WordPress XML (WXR) format: {e!s}",
        ) from e

    items: list[dict] = []

    for item in root.findall(".//item"):
        # Only import posts and pages; skip attachments, nav_menu_items, etc.
        post_type = item.findtext(f"{{{_WP_NS}}}post_type") or "post"
        if post_type not in ("post", "page"):
            continue

        title = item.findtext("title") or ""
        body = item.findtext(f"{{{_WP_CONTENT_NS}}}encoded") or item.findtext("description") or ""
        slug = item.findtext(f"{{{_WP_NS}}}post_name") or ""
        wp_status = item.findtext(f"{{{_WP_NS}}}status") or "draft"
        creator = item.findtext(f"{{{_WP_DC_NS}}}creator") or ""

        # Collect categories / tags
        categories = [c.text for c in item.findall("category[@domain='category']") if c.text]
        tags = [t.text for t in item.findall("category[@domain='post_tag']") if t.text]

        record: dict = {
            "title": title,
            "body": body,
            "slug": slug or None,
            "status": _WP_STATUS_MAP.get(wp_status, "draft"),
            "category": categories[0] if categories else None,
            "tags": ", ".join(tags) if tags else None,
            "_wp_creator": creator,  # informational — author is set to importer
        }
        items.append(record)

    return items


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """
    Split a Markdown file into (frontmatter dict, body).

    Expects YAML-like frontmatter delimited by '---' lines.
    Values are parsed as plain strings (no YAML library needed).
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm_text = parts[1].strip()
    body = parts[2].strip()

    metadata: dict = {}
    for line in fm_text.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.startswith("[") and value.endswith("]"):
            # Simple list: [a, b, c]
            value = value[1:-1]
        metadata[key] = value

    return metadata, body


async def parse_markdown_content(file_content: bytes) -> list[dict]:
    """
    Parse a Markdown file with YAML frontmatter into a content record.

    The file must contain at least a 'title' key in its frontmatter.
    Returns a list with a single dict (one file = one content item).
    """
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is not valid UTF-8: {e!s}",
        ) from e

    metadata, body = _parse_frontmatter(text)

    record: dict = {
        "title": metadata.get("title") or "",
        "body": body,
        "slug": metadata.get("slug") or None,
        "status": metadata.get("status", "draft"),
        "category": metadata.get("category") or None,
        "tags": metadata.get("tags") or None,
        "meta_title": metadata.get("meta_title") or None,
        "meta_description": metadata.get("meta_description") or None,
        "meta_keywords": metadata.get("meta_keywords") or None,
    }

    return [record]


async def import_content_wordpress(
    db: AsyncSession,
    file: UploadFile,
    user_id: int,
    name: str | None = None,
    duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP,
) -> ImportJob:
    """Import content from a WordPress WXR XML file."""
    file_content = await file.read()

    # Store as XML format (WXR is XML-based)
    job = await create_import_job(
        db=db,
        name=name or f"WordPress import - {file.filename}",
        import_type=ImportType.CONTENT,
        import_format=ImportFormat.XML,
        file_name=file.filename or "wordpress_export.xml",
        created_by_id=user_id,
        duplicate_handling=duplicate_handling,
        field_mapping=None,
    )
    job.file_size = len(file_content)
    await db.commit()

    records = await parse_wordpress_xml(file_content)
    return await process_content_import(db, job, records, user_id)


async def import_content_markdown(
    db: AsyncSession,
    file: UploadFile,
    user_id: int,
    name: str | None = None,
    duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP,
) -> ImportJob:
    """Import a single Markdown file with YAML frontmatter as a content item."""
    file_content = await file.read()

    # Store as JSON format (markdown is converted to a dict)
    job = await create_import_job(
        db=db,
        name=name or f"Markdown import - {file.filename}",
        import_type=ImportType.CONTENT,
        import_format=ImportFormat.JSON,
        file_name=file.filename or "content.md",
        created_by_id=user_id,
        duplicate_handling=duplicate_handling,
        field_mapping=None,
    )
    job.file_size = len(file_content)
    await db.commit()

    records = await parse_markdown_content(file_content)
    return await process_content_import(db, job, records, user_id)


async def import_content(
    db: AsyncSession,
    file: UploadFile,
    import_format: ImportFormat,
    user_id: int,
    name: str | None = None,
    duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP,
    field_mapping: dict | None = None,
) -> ImportJob:
    """Import content from uploaded file."""
    file_content = await file.read()

    # Create job
    job = await create_import_job(
        db=db,
        name=name or f"Content import - {file.filename}",
        import_type=ImportType.CONTENT,
        import_format=import_format,
        file_name=file.filename or "unknown",
        created_by_id=user_id,
        duplicate_handling=duplicate_handling,
        field_mapping=field_mapping,
    )
    job.file_size = len(file_content)
    await db.commit()

    # Parse file based on format
    if import_format == ImportFormat.JSON:
        records = await parse_json_content(file_content)
    elif import_format == ImportFormat.CSV:
        records = await parse_csv_content(file_content)
    elif import_format == ImportFormat.XML:
        records = await parse_xml_content(file_content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {import_format}",
        )

    # Process the import
    return await process_content_import(db, job, records, user_id)


async def import_users(
    db: AsyncSession,
    file: UploadFile,
    import_format: ImportFormat,
    user_id: int,
    name: str | None = None,
    duplicate_handling: DuplicateHandling = DuplicateHandling.SKIP,
    field_mapping: dict | None = None,
) -> ImportJob:
    """Import users from uploaded file."""
    file_content = await file.read()

    job = await create_import_job(
        db=db,
        name=name or f"User import - {file.filename}",
        import_type=ImportType.USERS,
        import_format=import_format,
        file_name=file.filename or "unknown",
        created_by_id=user_id,
        duplicate_handling=duplicate_handling,
        field_mapping=field_mapping,
    )
    job.file_size = len(file_content)
    await db.commit()

    # Parse file
    if import_format == ImportFormat.JSON:
        records = await parse_json_content(file_content)
    elif import_format == ImportFormat.CSV:
        records = await parse_csv_content(file_content)
    elif import_format == ImportFormat.XML:
        records = await parse_xml_content(file_content)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format: {import_format}",
        )

    return await process_user_import(db, job, records)


async def get_import_records(
    db: AsyncSession,
    job_id: int,
    status_filter: ImportStatus | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[ImportRecord]:
    """Get records for an import job."""
    query = select(ImportRecord).where(ImportRecord.import_job_id == job_id).order_by(ImportRecord.row_number)

    if status_filter:
        query = query.where(ImportRecord.status == status_filter)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def cancel_import_job(db: AsyncSession, job_id: int, user_id: int) -> ImportJob:
    """Cancel a pending or processing import job."""
    job = await get_import_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    if job.created_by_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this job",
        )

    if job.status not in [ImportStatus.PENDING, ImportStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = ImportStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job
