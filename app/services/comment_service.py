"""
Comment Service

Provides CRUD operations for comments with moderation support.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.comment import Comment, CommentStatus
from app.models.comment_engagement import (
    CommentEditHistory,
    CommentReaction,
    CommentReport,
    ReactionType,
    ReportReason,
    ReportStatus,
)
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

        # Save edit history before updating
        history_entry = CommentEditHistory(
            comment_id=comment.id,
            previous_body=comment.body,
            edited_by=user_id,
            edited_at=datetime.now(timezone.utc),
        )
        self.db.add(history_entry)

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

    # ==================== Reactions ====================

    async def toggle_reaction(
        self,
        comment_id: int,
        user_id: int,
        reaction_type: ReactionType,
    ) -> dict:
        """
        Toggle a reaction on a comment.

        - If no reaction exists, create one.
        - If same reaction type exists, remove it (toggle off).
        - If different reaction type exists, switch to the new type.

        Returns reaction counts and user's current reaction.
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            raise ValueError(f"Comment with ID {comment_id} not found")

        # Check for existing reaction
        result = await self.db.execute(
            select(CommentReaction).where(
                and_(
                    CommentReaction.comment_id == comment_id,
                    CommentReaction.user_id == user_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            if existing.reaction_type == reaction_type:
                # Same type — toggle off (remove)
                await self.db.delete(existing)
            else:
                # Different type — switch
                existing.reaction_type = reaction_type
        else:
            # No existing reaction — create
            reaction = CommentReaction(
                comment_id=comment_id,
                user_id=user_id,
                reaction_type=reaction_type,
            )
            self.db.add(reaction)

        await self.db.commit()

        counts = await self.get_reaction_counts(comment_id)
        user_reaction = await self.get_user_reaction(comment_id, user_id)

        return {
            **counts,
            "user_reaction": user_reaction.value if user_reaction else None,
        }

    async def get_reaction_counts(self, comment_id: int) -> dict:
        """Get like/dislike counts for a comment."""
        result = await self.db.execute(
            select(
                func.count(CommentReaction.id)
                .filter(CommentReaction.reaction_type == ReactionType.LIKE)
                .label("likes"),
                func.count(CommentReaction.id)
                .filter(CommentReaction.reaction_type == ReactionType.DISLIKE)
                .label("dislikes"),
            ).where(CommentReaction.comment_id == comment_id)
        )
        row = result.one()
        return {"like_count": row.likes or 0, "dislike_count": row.dislikes or 0}

    async def get_user_reaction(self, comment_id: int, user_id: int) -> ReactionType | None:
        """Get a user's reaction on a comment, or None."""
        result = await self.db.execute(
            select(CommentReaction.reaction_type).where(
                and_(
                    CommentReaction.comment_id == comment_id,
                    CommentReaction.user_id == user_id,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row

    # ==================== Reporting ====================

    async def report_comment(
        self,
        comment_id: int,
        user_id: int,
        reason: ReportReason,
        description: str | None = None,
    ) -> CommentReport:
        """
        Report a comment. Each user can only report a comment once.
        Auto-flags the comment if the report count meets the threshold.
        """
        comment = await self.db.get(Comment, comment_id)
        if not comment:
            raise ValueError(f"Comment with ID {comment_id} not found")

        # Check for duplicate report
        existing = await self.db.execute(
            select(CommentReport).where(
                and_(
                    CommentReport.comment_id == comment_id,
                    CommentReport.user_id == user_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("You have already reported this comment")

        report = CommentReport(
            comment_id=comment_id,
            user_id=user_id,
            reason=reason,
            description=description,
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        # Auto-flag: check report count against threshold
        count_result = await self.db.execute(
            select(func.count(CommentReport.id)).where(CommentReport.comment_id == comment_id)
        )
        report_count = count_result.scalar() or 0

        if report_count >= settings.comment_report_auto_flag_threshold and comment.status != CommentStatus.SPAM:
            comment.status = CommentStatus.PENDING
            comment.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.warning(f"Comment {comment_id} auto-flagged after {report_count} reports")

        logger.info(f"Comment reported: comment={comment_id}, user={user_id}, reason={reason.value}")
        return report

    async def get_comment_reports(
        self,
        comment_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> list[CommentReport]:
        """Get reports for a specific comment."""
        result = await self.db.execute(
            select(CommentReport)
            .where(CommentReport.comment_id == comment_id)
            .order_by(CommentReport.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_reports(
        self,
        skip: int = 0,
        limit: int = 50,
    ) -> list[CommentReport]:
        """Get all pending reports for moderation."""
        result = await self.db.execute(
            select(CommentReport)
            .where(CommentReport.status == ReportStatus.PENDING)
            .order_by(CommentReport.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def review_report(
        self,
        report_id: int,
        reviewer_id: int,
        status: ReportStatus,
    ) -> CommentReport | None:
        """Mark a report as reviewed or dismissed."""
        report = await self.db.get(CommentReport, report_id)
        if not report:
            return None

        report.status = status
        report.reviewed_by = reviewer_id
        report.reviewed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(report)

        logger.info(f"Report reviewed: id={report_id}, status={status.value}, reviewer={reviewer_id}")
        return report

    # ==================== Edit History ====================

    async def get_edit_history(self, comment_id: int) -> list[CommentEditHistory]:
        """Get edit history for a comment, newest first."""
        result = await self.db.execute(
            select(CommentEditHistory)
            .where(CommentEditHistory.comment_id == comment_id)
            .order_by(CommentEditHistory.edited_at.desc())
        )
        return list(result.scalars().all())


# Dependency for FastAPI
async def get_comment_service(db: AsyncSession) -> CommentService:
    """FastAPI dependency for CommentService."""
    return CommentService(db)
