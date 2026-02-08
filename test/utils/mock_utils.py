"""
Mock utilities for creating test data

Provides helper functions for creating test entities like content, categories, tags, etc.
"""

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.tag import Tag
from app.utils.slugify import slugify


async def create_test_content(
    db_session,
    title: str,
    body: str,
    author_id: int,
    status: ContentStatus = ContentStatus.DRAFT,
    category_id: int | None = None,
    description: str | None = None,
    meta_keywords: str | None = None,
):
    """Create a test content item with eagerly loaded relationships"""
    content = Content(
        title=title,
        slug=slugify(title),
        body=body,
        author_id=author_id,
        status=status,
        category_id=category_id,
        description=description,
        meta_keywords=meta_keywords,
    )
    db_session.add(content)
    await db_session.commit()
    await db_session.refresh(content, attribute_names=["tags", "category", "author"])
    return content


async def create_test_category(db_session, name: str, description: str = "Test category"):
    """Create a test category"""
    category = Category(
        name=name,
        description=description,
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


async def create_test_tag(db_session, name: str):
    """Create a test tag"""
    tag = Tag(name=name)
    db_session.add(tag)
    await db_session.commit()
    await db_session.refresh(tag)
    return tag
