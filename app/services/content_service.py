from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.content import Content
from app.schemas.content import ContentCreate
from datetime import datetime
import logging

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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
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

    return new_content
