"""GraphQL Mutation resolvers."""

import strawberry
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.graphql.context import GraphQLContext
from app.graphql.types import ContentInput, ContentType, ContentUpdateInput, content_to_type
from app.models.content import Content
from app.models.user import User
from app.schemas.content import ContentCreate, ContentUpdate
from app.services import content_service


def _require_auth(info: Info[GraphQLContext, None]) -> User:
    """Raise an error if the request is unauthenticated."""
    if not info.context.user:
        raise ValueError("Authentication required")
    return info.context.user


@strawberry.type
class Mutation:
    """Root GraphQL mutation type."""

    @strawberry.mutation(description="Create a new content draft. Requires authentication.")
    async def create_content(
        self,
        info: Info[GraphQLContext, None],
        input: ContentInput,
    ) -> ContentType:
        user = _require_auth(info)
        db = info.context.db

        content_data = ContentCreate(
            title=input.title,
            body=input.body,
            description=input.description,
            status=input.status,
        )

        try:
            new_content = await content_service.create_content(db, content_data)
            # Patch author_id since service doesn't accept current_user
            new_content.author_id = user.id
            await db.commit()
            await db.refresh(new_content)
        except Exception as e:
            await db.rollback()
            raise ValueError(f"Failed to create content: {e}") from e

        # Reload with relationships
        result = await db.execute(
            select(Content)
            .where(Content.id == new_content.id)
            .options(
                selectinload(Content.author).selectinload(User.role),
                selectinload(Content.category),
                selectinload(Content.tags),
            )
        )
        item = result.scalars().first()
        return content_to_type(item)

    @strawberry.mutation(description="Update a content item. Requires authentication and ownership (or admin).")
    async def update_content(
        self,
        info: Info[GraphQLContext, None],
        id: int,
        input: ContentUpdateInput,
    ) -> ContentType | None:
        user = _require_auth(info)
        db = info.context.db

        result = await db.execute(
            select(Content).where(Content.id == id).options(selectinload(Content.author).selectinload(User.role))
        )
        existing = result.scalars().first()
        if not existing:
            return None

        is_admin = user.role and user.role.name in ("admin", "superadmin")
        if existing.author_id != user.id and not is_admin:
            raise ValueError("Permission denied: you do not own this content")

        update_data = ContentUpdate(
            title=input.title,
            body=input.body,
            description=input.description,
        )

        try:
            await content_service.update_content(id, update_data, db, user)
        except (HTTPException, Exception) as e:
            raise ValueError(str(e)) from e

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
        return content_to_type(item) if item else None
