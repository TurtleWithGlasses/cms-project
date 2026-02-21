"""GraphQL context — carries the current user and DB session into resolvers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from strawberry.fastapi import BaseContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User


class GraphQLContext(BaseContext):
    """Context passed to every GraphQL resolver."""

    def __init__(self, user: User | None, db: AsyncSession) -> None:
        super().__init__()
        self.user = user
        self.db = db
