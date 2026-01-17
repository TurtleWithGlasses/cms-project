"""
Comment Service

Provides CRUD operations for comments with moderation support.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment, CommentStatus
from app.models.content import Content

logger = logging.getLogger(__name__)


class CommentService:
    """Service for managing comments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_comment(
        self,
        content_id: int,
        user_id: int,
        body: str,
        parent_id: int | None = None,
        auto_approve: bool = False,
    ) -> Comment:
        """
        Create a new comment.

        Args:
            content_id: ID of the content being commented on
            user_id: ID of the user creating the comment
            body: Comment text
            parent_id: Optional parent comment ID for replies
            auto_approve: If True, automatically approve the comment

        Returns:
            Created comment instance
        """
        # Verify content exists
        content = await self.db.get(Content, content_id)
        if not content:
            raise ValueError(f"Content with ID {content_id} not found")

        # Verify parent comment exists if provided
        if parent_id:
            parent = await self.db.get(Comment, parent_id)
            if not parent:
                raise ValueError(f"Parent comment with ID {parent_id} not found")
            if parent.content_id != content_id:
                raise ValueError("Parent comment belongs to different content")

        status = CommentStatus.APPROVED if auto_approve else CommentStatus.PENDING

        comment = Comment(
            content_id=content_id,
            user_id=user_id,
            body=body,
            parent_id=parent_id,
            status=status,
        )

        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)

        logger.info(f"Comment created: id={comment.id}, content={content_id}, user={user_id}")
        return comment

    async def get_comment(self, comment_id: int) -> Comment | None:
        """Get a comment by ID with user and replies loaded."""
        result = await self.db.execute(
            select(Comment)
            .options(
                selectinload(Comment.user),
                selectinload(Comment.replies).selectinload(Comment.user),
            )
            .where(Comment.id == comment_id)
        )
        return result.scalar_one_or_none()

    async def get_comments_for_content(
        self,
        content_id: int,
        include_pending: bool = False,
        include_replies: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Comment]:
        """
        Get top-level comments for a content item.

        Args:
            content_id: ID of the content
            include_pending: Include pending (unmoderated) comments
            include_replies: Load nested replies
            skip: Number of comments to skip
            limit: Maximum number of comments to return

        Returns:
            List of top-level comments
        """
        query = select(Comment).where(
            and_(
                Comment.content_id == content_id,
                Comment.parent_id.is_(None),  # Top-level only
                Comment.is_deleted.is_(False),
            )
        )

        if not include_pending:
            query = query.where(Comment.status == CommentStatus.APPROVED)

        if include_replies:
            query = query.options(
                selectinload(Comment.user),
                selectinload(Comment.replies).selectinload(Comment.user),
            )
        else:
            query = query.options(selectinload(Comment.user))

        query = query.order_by(Comment.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_comment_count(
        self,
        content_id: int,
        include_pending: bool = False,
    ) -> int:
        """Get total comment count for a content item."""
        query = select(func.count(Comment.id)).where(
            and_(
                Comment.content_id == content_id,
                Comment.is_deleted.is_(False),
            )
        )

        if not include_pending:
            query = query.where(Comment.status == CommentStatus.APPROVED)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def update_comment(
        self,
        comment_id: int,
        user_id: int,
        body: str,
    ) -> Comment | None:
        """
        Update a comment's body.

        Only the original author can update their comment.
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            return None

        if comment.user_id != user_id:
            raise PermissionError("Only the author can edit this comment")

        if comment.is_deleted:
            raise ValueError("Cannot edit a deleted comment")

        comment.body = body
        comment.is_edited = True
        comment.edited_at = datetime.now(timezone.utc)
        comment.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(comment)

        logger.info(f"Comment updated: id={comment_id}")
        return comment

    async def delete_comment(
        self,
        comment_id: int,
        user_id: int,
        is_admin: bool = False,
    ) -> bool:
        """
        Soft delete a comment.

        Authors can delete their own comments.
        Admins can delete any comment.
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            return False

        if not is_admin and comment.user_id != user_id:
            raise PermissionError("Only the author or admin can delete this comment")

        comment.is_deleted = True
        comment.updated_at = datetime.now(timezone.utc)

        await self.db.commit()

        logger.info(f"Comment deleted: id={comment_id}, by_user={user_id}")
        return True

    async def moderate_comment(
        self,
        comment_id: int,
        status: CommentStatus,
        moderator_id: int,
    ) -> Comment | None:
        """
        Moderate a comment (approve, reject, or mark as spam).

        Only moderators/admins should call this.
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            return None

        old_status = comment.status
        comment.status = status
        comment.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(comment)

        logger.info(
            f"Comment moderated: id={comment_id}, status={old_status.value}->{status.value}, moderator={moderator_id}"
        )
        return comment

    async def get_pending_comments(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Comment]:
        """Get all pending comments for moderation queue."""
        query = (
            select(Comment)
            .options(
                selectinload(Comment.user),
                selectinload(Comment.content),
            )
            .where(
                and_(
                    Comment.status == CommentStatus.PENDING,
                    Comment.is_deleted.is_(False),
                )
            )
            .order_by(Comment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user_comments(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Comment]:
        """Get all comments by a specific user."""
        query = (
            select(Comment)
            .options(selectinload(Comment.content))
            .where(
                and_(
                    Comment.user_id == user_id,
                    Comment.is_deleted.is_(False),
                )
            )
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def bulk_moderate(
        self,
        comment_ids: list[int],
        status: CommentStatus,
        moderator_id: int,
    ) -> int:
        """
        Bulk moderate multiple comments.

        Returns the number of comments updated.
        """
        count = 0
        for comment_id in comment_ids:
            result = await self.moderate_comment(comment_id, status, moderator_id)
            if result:
                count += 1

        logger.info(f"Bulk moderation: {count} comments set to {status.value}")
        return count


# Dependency for FastAPI
async def get_comment_service(db: AsyncSession) -> CommentService:
    """FastAPI dependency for CommentService."""
    return CommentService(db)
