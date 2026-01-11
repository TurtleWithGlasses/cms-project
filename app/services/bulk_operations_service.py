"""
Bulk Operations Service

Handles bulk operations on content, users, and other entities for efficiency.
"""

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.content import Content, ContentStatus
from app.models.user import User
from app.utils.activity_log import log_activity


class BulkOperationsService:
    """Service for performing bulk operations on entities"""

    @staticmethod
    async def bulk_publish_content(
        content_ids: list[int],
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk publish content items.

        Args:
            content_ids: List of content IDs to publish
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success count and failed IDs
        """
        # Verify all content exists and user has permission
        stmt = select(Content).where(Content.id.in_(content_ids))
        result = await db.execute(stmt)
        content_items = result.scalars().all()

        if not content_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No content found with provided IDs")

        # Update status to published
        success_ids = []
        failed_ids = []

        for content in content_items:
            try:
                if content.status == ContentStatus.PENDING:
                    content.status = ContentStatus.PUBLISHED

                    # Log activity
                    await log_activity(
                        action="content_bulk_published",
                        user_id=current_user.id,
                        description=f"Bulk published content: {content.title}",
                        content_id=content.id,
                    )
                    success_ids.append(content.id)
                else:
                    failed_ids.append(
                        {
                            "id": content.id,
                            "reason": f"Content must be in pending status, currently {content.status.value}",
                        }
                    )
            except Exception as e:
                failed_ids.append({"id": content.id, "reason": str(e)})

        await db.commit()

        return {
            "success_count": len(success_ids),
            "success_ids": success_ids,
            "failed_count": len(failed_ids),
            "failed_items": failed_ids,
        }

    @staticmethod
    async def bulk_update_content_status(
        content_ids: list[int],
        new_status: str,
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk update content status.

        Args:
            content_ids: List of content IDs
            new_status: New status to set
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success/failure counts
        """
        # Validate status
        try:
            status_enum = ContentStatus(new_status)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {new_status}"
            ) from err

        # Fetch content
        stmt = select(Content).where(Content.id.in_(content_ids))
        result = await db.execute(stmt)
        content_items = result.scalars().all()

        if not content_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No content found")

        success_ids = []
        failed_ids = []

        for content in content_items:
            try:
                old_status = content.status
                content.status = status_enum

                await log_activity(
                    action="content_status_bulk_updated",
                    user_id=current_user.id,
                    description=f"Changed status from {old_status.value} to {new_status}",
                    content_id=content.id,
                )
                success_ids.append(content.id)
            except Exception as e:
                failed_ids.append({"id": content.id, "reason": str(e)})

        await db.commit()

        return {
            "success_count": len(success_ids),
            "success_ids": success_ids,
            "failed_count": len(failed_ids),
            "failed_items": failed_ids,
        }

    @staticmethod
    async def bulk_delete_content(
        content_ids: list[int],
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk delete content items.

        Args:
            content_ids: List of content IDs to delete
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success/failure counts
        """
        # Fetch content to verify existence and log before deletion
        stmt = select(Content).where(Content.id.in_(content_ids))
        result = await db.execute(stmt)
        content_items = result.scalars().all()

        if not content_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No content found")

        # Log deletions
        for content in content_items:
            await log_activity(
                action="content_bulk_deleted",
                user_id=current_user.id,
                description=f"Bulk deleted content: {content.title}",
                content_id=content.id,
            )

        # Delete content
        deleted_ids = [c.id for c in content_items]
        stmt = delete(Content).where(Content.id.in_(content_ids))
        await db.execute(stmt)
        await db.commit()

        return {
            "success_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
        }

    @staticmethod
    async def bulk_assign_tags(
        content_ids: list[int],
        tag_ids: list[int],
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk assign tags to content.

        Args:
            content_ids: List of content IDs
            tag_ids: List of tag IDs to assign
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success/failure counts
        """
        # Verify content exists
        stmt = select(Content).where(Content.id.in_(content_ids))
        result = await db.execute(stmt)
        content_items = result.scalars().all()

        if not content_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No content found")

        # Verify tags exist
        from app.models.tag import Tag

        stmt = select(Tag).where(Tag.id.in_(tag_ids))
        result = await db.execute(stmt)
        tags = result.scalars().all()

        if len(tags) != len(tag_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more tags not found")

        success_count = 0

        for content in content_items:
            try:
                # Add tags (avoiding duplicates)
                for tag in tags:
                    if tag not in content.tags:
                        content.tags.append(tag)

                await log_activity(
                    action="tags_bulk_assigned",
                    user_id=current_user.id,
                    description=f"Assigned {len(tag_ids)} tags to content",
                    content_id=content.id,
                )
                success_count += 1
            except Exception as e:
                print(f"Error assigning tags to content {content.id}: {e}")

        await db.commit()

        return {
            "success_count": success_count,
            "tags_assigned": len(tag_ids),
        }

    @staticmethod
    async def bulk_update_category(
        content_ids: list[int],
        category_id: int,
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk update content category.

        Args:
            content_ids: List of content IDs
            category_id: New category ID
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success/failure counts
        """
        # Verify category exists
        from app.models.category import Category

        stmt = select(Category).where(Category.id == category_id)
        result = await db.execute(stmt)
        category = result.scalars().first()

        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        # Update content
        stmt = update(Content).where(Content.id.in_(content_ids)).values(category_id=category_id)
        result = await db.execute(stmt)
        await db.commit()

        updated_count = result.rowcount  # type: ignore[attr-defined]

        # Log activity
        await log_activity(
            action="category_bulk_updated",
            user_id=current_user.id,
            description=f"Updated category for {updated_count} content items to {category.name}",
        )

        return {
            "success_count": updated_count,
            "new_category": category.name,
        }

    @staticmethod
    async def bulk_update_user_roles(
        user_ids: list[int],
        role_id: int,
        current_user: User,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """
        Bulk update user roles.

        Args:
            user_ids: List of user IDs
            role_id: New role ID
            current_user: User performing the operation
            db: Database session

        Returns:
            Dict with success/failure counts
        """
        # Verify role exists
        from app.models.user import Role

        stmt = select(Role).where(Role.id == role_id)
        result = await db.execute(stmt)
        role = result.scalars().first()

        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        # Don't allow changing superadmin roles
        stmt = select(User).where(User.id.in_(user_ids))
        result = await db.execute(stmt)
        users = result.scalars().all()

        success_ids = []
        failed_ids = []

        for user in users:
            if user.id == current_user.id:
                failed_ids.append({"id": user.id, "reason": "Cannot change your own role"})
                continue

            if user.role.name == "superadmin":
                failed_ids.append({"id": user.id, "reason": "Cannot change superadmin role"})
                continue

            user.role_id = role_id
            success_ids.append(user.id)

            await log_activity(
                action="user_role_bulk_updated",
                user_id=current_user.id,
                description=f"Changed user {user.username} role to {role.name}",
                target_user_id=user.id,
            )

        await db.commit()

        return {
            "success_count": len(success_ids),
            "success_ids": success_ids,
            "failed_count": len(failed_ids),
            "failed_items": failed_ids,
            "new_role": role.name,
        }


# Singleton instance
bulk_operations_service = BulkOperationsService()
