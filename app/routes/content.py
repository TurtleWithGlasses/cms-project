from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.models.content import Content, ContentStatus
from app.models.notification import Notification
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate
from app.database import get_db
from app.utils.slugify import slugify
from app.auth import get_current_user_with_role
from app.utils.auth_helpers import get_current_user
from app.utils.activity_log import log_activity
from datetime import datetime
# from functools import partial
import logging

from app.models.activity_log import ActivityLog

logging.basicConfig(
    level=logging.INFO,  # Set the desired log level (INFO, DEBUG, etc.)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

router = APIRouter()

async def fetch_content_by_id(content_id: int, db: AsyncSession) -> Content:
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalars().first()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content

def validate_content_status(content: Content, required_status: ContentStatus):
    if content.status != required_status:
        raise HTTPException(
            status_code=400,
            detail=f"Content must be in {required_status.value} status."
        )

@router.post("/content", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    content: ContentCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    try:
        slug = content.slug or slugify(content.title)

        # Create new content
        new_content = Content(
            title=content.title,
            body=content.body,
            slug=slug,
            description=content.description,
            status=ContentStatus.DRAFT,
            meta_title=content.meta_title,
            meta_description=content.meta_description,
            meta_keywords=content.meta_keywords,
            author_id=current_user.id,
            created_at=datetime.utcnow(),
        )
        db.add(new_content)
        await db.commit()
        await db.refresh(new_content)

        # Log activity using a separate session
        try:
            await log_activity(
                action="create_draft",
                user_id=current_user.id,
                content_id=new_content.id,
                description=f"User {current_user.username} created draft content with ID {new_content.id}.",
                details={
                    "title": new_content.title,
                    "slug": new_content.slug,
                    "status": new_content.status.value,
                },
            )
        except Exception as e:
            logger.warning(f"Activity logging failed: {e}")

        return new_content

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create content: {str(e)}")

@router.patch("/content/{content_id}", response_model=ContentResponse)
async def update_content(content_id: int, content: ContentUpdate, db: AsyncSession = Depends(get_db)):
    # Fetch content with eager loading
    existing_content = await db.execute(
        select(Content)
        .options(selectinload(Content.author))  # Add all necessary relationships
        .where(Content.id == content_id)
    )
    existing_content = existing_content.scalars().first()

    if not existing_content:
        raise HTTPException(status_code=404, detail="Content not found.")

    # Validate slug
    if content.slug:
        slug = content.slug
        result = await db.execute(select(Content).where(Content.slug == slug, Content.id != content_id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")
        existing_content.slug = slug
    else:
        existing_content.slug = slugify(content.title)

    # Update fields
    existing_content.title = content.title or existing_content.title
    existing_content.body = content.body or existing_content.body
    existing_content.meta_title = content.meta_title or existing_content.meta_title
    existing_content.meta_description = content.meta_description or existing_content.meta_description
    existing_content.meta_keywords = content.meta_keywords or existing_content.meta_keywords
    existing_content.updated_at = datetime.utcnow()

    try:
        # Commit updates
        await db.commit()
        await db.refresh(existing_content)

        # Log the activity
        try:
            await log_activity(
                action="update_content",
                user_id=existing_content.author_id,
                content_id=content_id,
                description=f"Content with ID {content_id} updated.",
                details={"updated_fields": list(content.dict(exclude_unset=True).keys())},
                db=db,
            )
        except Exception as log_error:
            logger.warning(f"Failed to log activity for updated content {content_id}: {log_error}")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}")

    return existing_content

@router.patch("/content/{content_id}/submit", response_model=ContentResponse)
async def submit_for_approval(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(["editor", "admin"])),
):
    logger.debug(f"DB session at start: {db}")
    content = await fetch_content_by_id(content_id, db)
    validate_content_status(content, ContentStatus.DRAFT)

    content.status = ContentStatus.PENDING
    content.updated_at = datetime.utcnow()

    details = {
        "id": content.id,
        "title": content.title,
        "slug": content.slug,
        "status": content.status,
        "description": content.description,
    }

    try:
        # Log activity within the same session and transaction
        new_log = ActivityLog(
            action="content_submission",
            user_id=current_user.id,
            content_id=content.id,
            description=f"Content with ID {content.id} submitted for approval.",
            details=details,
            timestamp=datetime.utcnow(),
        )
        db.add(new_log)

        # Commit both the content update and the log
        await db.commit()
        logger.info(f"Content {content_id} submitted for approval by user {current_user.id}")
    except Exception as e:
        logger.error(f"Failed to submit content {content_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit content: {str(e)}")

    return content

@router.patch("/content/{content_id}/approve", response_model=ContentResponse)
async def approve_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_with_role(["admin"])),
):
    try:
        # Fetch content and validate its current status
        content = await fetch_content_by_id(content_id, db)
        validate_content_status(content, ContentStatus.PENDING)

        # Update content status and timestamps
        content.status = ContentStatus.PUBLISHED
        content.publish_date = datetime.utcnow()
        content.updated_at = datetime.utcnow()

        # Prepare details for logging
        details = {
            "id": content.id,
            "title": content.title,
            "slug": content.slug,
            "status": content.status.value,  # Ensure Enum values are serialized
            "description": content.description,
        }

        # Add the log entry to the same session
        new_log = ActivityLog(
            action="content_approval",
            user_id=current_user.id,
            content_id=content.id,
            description=f"Content with ID {content.id} approved and published.",
            details=details,
            timestamp=datetime.utcnow(),
        )
        db.add(new_log)

        await db.commit()

        await db.refresh(content)

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve content: {str(e)}")

    finally:
        # Ensure session cleanup
        await db.close()

    return content
