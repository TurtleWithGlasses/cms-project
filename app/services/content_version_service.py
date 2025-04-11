from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import NoResultFound
from app.models.content import Content
from app.models.content_version import ContentVersion
from app.models.user import User
from fastapi import HTTPException, status

async def create_version_from_content(content: Content, db: AsyncSession, current_user: User):
    version = ContentVersion(
        content_id=content.id,
        title=content.title,
        body=content.body,
        meta_title=content.meta_title,
        meta_description=content.meta_description,
        meta_keywords=content.meta_keywords,
        slug=content.slug,
        status=content.status,
        author_id=current_user.id
    )
    db.add(version)
    await db.commit()

async def get_versions(content_id: int, db: AsyncSession):
    result = await db.execute(
        select(ContentVersion).where(ContentVersion.content_id == content_id).order_by(ContentVersion.created_at.desc())
    )
    return result.scalars().all()

async def rollback_to_version(content_id: int, version_id: int, db: AsyncSession, current_user: User):
    result = await db.execute(select(ContentVersion).where(ContentVersion.id == version_id, ContentVersion.content_id == content_id))
    version = result.scalars().first()

    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalars().first()

    if not content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    
    # Create backup version before rollback
    await create_version_from_content(content, db, current_user)

    content.title = version.title
    content.body = version.body
    content.meta_title = version.meta_title
    content.meta_description = version.meta_description
    content.meta_keywords = version.meta_keywords
    content.slug = version.slug
    content.status = version.status

    await db.commit()
    await db.refresh(content)
    return content