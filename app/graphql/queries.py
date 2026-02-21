"""GraphQL Query resolvers."""

import strawberry
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.types import (
    CategoryType,
    CommentType,
    ContentType,
    UserType,
    category_to_type,
    comment_to_type,
    content_to_type,
    user_to_type,
)
from app.models.category import Category
from app.models.comment import Comment, CommentStatus
from app.models.content import Content
from app.models.user import User
from app.services.content_service import get_all_content


@strawberry.type
class Query:
    """Root GraphQL query type."""

    @strawberry.field(description="Get the currently authenticated user, or null if unauthenticated.")
    async def me(self, info: Info[GraphQLContext, None]) -> UserType | None:
        user = info.context.user
        if not user:
            return None
        return user_to_type(user)

    @strawberry.field(description="Get a single content item by ID.")
    async def content(
        self,
        info: Info[GraphQLContext, None],
        id: int,
    ) -> ContentType | None:
        db = info.context.db
        result = await db.execute(
            select(Content)
            .where(Content.id == id)
            .options(
                selectinload(Content.author).selectinload(User.role),
                selectinload(Content.category),
                selectinload(Content.tags),
            )
        )
        item = result.scalars().first()
        if not item:
            return None
        return content_to_type(item)

    @strawberry.field(description="List content items with optional filters.")
    async def contents(
        self,
        info: Info[GraphQLContext, None],
        status: str | None = None,
        category_id: int | None = None,
        author_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ContentType]:
        db = info.context.db
        items = await get_all_content(
            db,
            skip=offset,
            limit=limit,
            status=status,
            category_id=category_id,
            author_id=author_id,
        )
        return [content_to_type(c) for c in items]

    @strawberry.field(description="List all categories.")
    async def categories(
        self,
        info: Info[GraphQLContext, None],
    ) -> list[CategoryType]:
        db = info.context.db
        result = await db.execute(select(Category).order_by(Category.name))
        cats = result.scalars().all()
        return [category_to_type(c) for c in cats]

    @strawberry.field(description="List approved comments for a content item.")
    async def comments(
        self,
        info: Info[GraphQLContext, None],
        content_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CommentType]:
        db = info.context.db
        result = await db.execute(
            select(Comment)
            .where(
                Comment.content_id == content_id,
                Comment.status == CommentStatus.APPROVED,
                Comment.is_deleted.is_(False),
            )
            .options(selectinload(Comment.user).selectinload(User.role))
            .order_by(Comment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        coms = result.scalars().all()
        return [comment_to_type(c) for c in coms]
