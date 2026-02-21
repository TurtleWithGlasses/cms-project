"""Strawberry GraphQL types mapped from CMS SQLAlchemy models."""

from datetime import datetime

import strawberry


@strawberry.type
class UserType:
    """A CMS user."""

    id: int
    username: str
    role_name: str


@strawberry.type
class CategoryType:
    """A content category."""

    id: int
    name: str
    slug: str
    parent_id: int | None


@strawberry.type
class TagType:
    """A content tag."""

    id: int
    name: str


@strawberry.type
class ContentType:
    """A CMS content item."""

    id: int
    title: str
    slug: str
    status: str
    description: str | None
    body: str | None
    created_at: datetime
    updated_at: datetime
    author: UserType
    category: CategoryType | None
    tags: list[TagType]


@strawberry.type
class CommentType:
    """A comment on a content item."""

    id: int
    body: str
    status: str
    created_at: datetime
    content_id: int
    author: UserType


# ============================================================================
# Input types
# ============================================================================


@strawberry.input
class ContentInput:
    """Input for creating a content item."""

    title: str
    body: str
    description: str | None = None
    status: str = "draft"


@strawberry.input
class ContentUpdateInput:
    """Input for updating a content item."""

    title: str | None = None
    body: str | None = None
    description: str | None = None
    status: str | None = None


# ============================================================================
# Helper conversion functions
# ============================================================================


def user_to_type(user) -> UserType:
    return UserType(
        id=user.id,
        username=user.username,
        role_name=user.role.name if user.role else "user",
    )


def category_to_type(cat) -> CategoryType:
    return CategoryType(
        id=cat.id,
        name=cat.name,
        slug=cat.slug,
        parent_id=cat.parent_id,
    )


def tag_to_type(tag) -> TagType:
    return TagType(id=tag.id, name=tag.name)


def content_to_type(content) -> ContentType:
    return ContentType(
        id=content.id,
        title=content.title,
        slug=content.slug,
        status=content.status.value if hasattr(content.status, "value") else str(content.status),
        description=content.description,
        body=content.body,
        created_at=content.created_at,
        updated_at=content.updated_at,
        author=user_to_type(content.author),
        category=category_to_type(content.category) if content.category else None,
        tags=[tag_to_type(t) for t in (content.tags or [])],
    )


def comment_to_type(comment) -> CommentType:
    return CommentType(
        id=comment.id,
        body=comment.body,
        status=comment.status.value if hasattr(comment.status, "value") else str(comment.status),
        created_at=comment.created_at,
        content_id=comment.content_id,
        author=user_to_type(comment.user),
    )
