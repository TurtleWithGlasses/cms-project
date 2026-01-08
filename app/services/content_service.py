import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# from sqlalchemy import select
from app.auth import hash_password
from app.models.content import Content
from app.models.user import User
from app.scheduler import schedule_content
from app.schemas.content import ContentCreate, ContentUpdate
from app.schemas.user import UserUpdate
from app.services import content_version_service

logger = logging.getLogger(__name__)


async def create_content(db: AsyncSession, content_data: ContentCreate) -> Content:
    """
    Creates a new content entry in the database.

    Args:
        db (AsyncSession): The database session.
        content_data (ContentCreate): The data for the new content.

    Returns:
        Content: The newly created content object.

    Raises:
        RuntimeError: If the content creation fails.
    """
    new_content = Content(
        title=content_data.title,
        body=content_data.body,
        status=content_data.status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_content)

    try:
        await db.commit()
        await db.refresh(new_content)
        logger.info(f"Content created successfully: {new_content.id}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating content: {str(e)}")
        raise RuntimeError(f"Failed to create content: {str(e)}") from e

    await db.refresh(new_content)
    logger.info(f"Content created successfully: {new_content.id}")
    if content_data.publish_at and content_data.status == "scheduled":
        schedule_content(new_content.id, content_data.publish_at)

    return new_content


async def update_content(content_id: int, data: ContentUpdate, db: AsyncSession, current_user: User):
    result = await db.execute(select(Content).where(Content.id == content_id))
    existing_content = result.scalars().first()

    if not existing_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    # Create version before applying updates
    await content_version_service.create_version_from_content(existing_content, db, current_user)

    # Apply updates
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(existing_content, field, value)

    await db.commit()
    await db.refresh(existing_content)

    if existing_content.publish_date and existing_content.status == "scheduled":
        schedule_content(existing_content.id, existing_content.publish_date)

    return existing_content


async def get_all_content(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status: str | None = None,
    category_id: int | None = None,
    author_id: int | None = None,
) -> list[Content]:
    query = select(Content)

    if category_id:
        query = query.where(Content.category_id == category_id)

    if status:
        query = query.where(Content.status == status)

    if author_id:
        query = query.where(Content.author_id == author_id)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_user_info(user_id: int, user_update: UserUpdate, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    user.username = user_update.username
    user.email = user_update.email

    if user_update.password:
        user.hashed_password = hash_password(user_update.password)  # 🔥 HASH it!

    await db.commit()
    await db.refresh(user)
    return user
