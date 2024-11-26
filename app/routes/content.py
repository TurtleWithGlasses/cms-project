from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.content import Content, ContentStatus
from app.models.notification import Notification
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate
from app.database import get_db
from app.utils.slugify import slugify
from ..auth import get_current_user, get_current_user_with_role
from ..utils.activity_log import log_activity
from datetime import datetime

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
async def create_draft(content: ContentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    slug = content.slug or slugify(content.title)

    result = await db.execute(select(Content).where(Content.slug == slug))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")

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
    try:
        await db.commit()
        await db.refresh(new_content)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create content: {str(e)}")

    return new_content

@router.patch("/content/{content_id}", response_model=ContentResponse)
async def update_content(content_id: int, content: ContentUpdate, db: AsyncSession = Depends(get_db)):
    existing_content = await fetch_content_by_id(content_id, db)

    if content.slug:
        slug = content.slug
        result = await db.execute(select(Content).where(Content.slug == slug, Content.id != content_id))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Slug already exists. Choose a unique URL.")
        existing_content.slug = slug
    else:
        existing_content.slug = slugify(content.title)

    existing_content.title = content.title or existing_content.title
    existing_content.body = content.body or existing_content.body
    existing_content.meta_title = content.meta_title or existing_content.meta_title
    existing_content.meta_description = content.meta_description or existing_content.meta_description
    existing_content.meta_keywords = content.meta_keywords or existing_content.meta_keywords
    existing_content.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(existing_content)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update content: {str(e)}")

    return existing_content

@router.patch("/content/{content_id}/submit", response_model=ContentResponse)
async def submit_for_approval(content_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_with_role(["editor", "admin"]))):
    content = await fetch_content_by_id(content_id, db)
    validate_content_status(content, ContentStatus.DRAFT)

    content.status = ContentStatus.PENDING
    content.updated_at = datetime.utcnow()
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit content: {str(e)}")

    result = await db.execute(select(User).where(User.role.in_(["admin", "editor"])))
    admins_and_editors = result.scalars().all()
    for user in admins_and_editors:
        notification = Notification(
            user_id=user.id,
            content_id=content_id,
            message=f"Content '{content.title}' is pending approval",
        )
        db.add(notification)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to notify admins/editors: {str(e)}")

    await log_activity(
        db=db,
        action="content_submission",
        user_id=current_user.id,
        content_id=content.id,
        description=f"Content with ID {content.id} submitted for approval.",
    )

    await db.refresh(content)
    return content

@router.patch("/content/{content_id}/approve", response_model=ContentResponse)
async def approve_content(content_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user_with_role(["admin"]))):
    content = await fetch_content_by_id(content_id, db)
    validate_content_status(content, ContentStatus.PENDING)

    content.status = ContentStatus.PUBLISHED
    content.publish_date = datetime.utcnow()
    content.updated_at = datetime.utcnow()

    try:
        await db.commit()
        await db.refresh(content)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve content: {str(e)}")

    await log_activity(
        db=db,
        action="content_approval",
        user_id=current_user.id,
        content_id=content.id,
        description=f"Content with ID {content.id} approved and published.",
    )
    return content
