"""
Export Service

Provides data export functionality in multiple formats (JSON, CSV).
"""

import csv
import json
from io import StringIO

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models.activity_log import ActivityLog
from app.models.content import Content
from app.models.user import User


class ExportService:
    """Service for exporting data in various formats"""

    @staticmethod
    async def export_content_json(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export content as JSON.

        Args:
            db: Database session
            status: Filter by status
            status: Filter by author
            limit: Maximum number of records

        Returns:
            JSON string
        """
        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )

        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for content in content_list:
            export_data.append(
                {
                    "id": content.id,
                    "title": content.title,
                    "slug": content.slug,
                    "body": content.body,
                    "status": content.status.value,
                    "author": {
                        "id": content.author.id,
                        "username": content.author.username,
                        "email": content.author.email,
                    },
                    "category": {
                        "id": content.category.id if content.category else None,
                        "name": content.category.name if content.category else None,
                    },
                    "tags": [{"id": tag.id, "name": tag.name} for tag in content.tags],
                    "created_at": content.created_at.isoformat(),
                    "updated_at": content.updated_at.isoformat() if content.updated_at else None,
                    "publish_at": content.publish_at.isoformat() if content.publish_at else None,
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_content_csv(
        db: AsyncSession,
        status: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export content as CSV.

        Args:
            db: Database session
            status: Filter by status
            author_id: Filter by author
            limit: Maximum number of records

        Returns:
            CSV string
        """
        stmt = select(Content).options(
            joinedload(Content.author),
            joinedload(Content.category),
            joinedload(Content.tags),
        )

        if status:
            stmt = stmt.where(Content.status == status)
        if author_id:
            stmt = stmt.where(Content.author_id == author_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        content_list = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Title",
                "Slug",
                "Status",
                "Author Username",
                "Author Email",
                "Category",
                "Tags",
                "Created At",
                "Updated At",
                "Publish At",
            ]
        )

        # Write data
        for content in content_list:
            writer.writerow(
                [
                    content.id,
                    content.title,
                    content.slug,
                    content.status.value,
                    content.author.username,
                    content.author.email,
                    content.category.name if content.category else "",
                    ", ".join([tag.name for tag in content.tags]),
                    content.created_at.isoformat(),
                    content.updated_at.isoformat() if content.updated_at else "",
                    content.publish_at.isoformat() if content.publish_at else "",
                ]
            )

        return output.getvalue()

    @staticmethod
    async def export_users_json(
        db: AsyncSession,
        role_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export users as JSON.

        Args:
            db: Database session
            role_id: Filter by role
            limit: Maximum number of records

        Returns:
            JSON string
        """
        stmt = select(User).options(joinedload(User.role))

        if role_id:
            stmt = stmt.where(User.role_id == role_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for user in users:
            export_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": {
                        "id": user.role.id,
                        "name": user.role.name,
                    },
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_users_csv(
        db: AsyncSession,
        role_id: int | None = None,
        limit: int | None = None,
    ) -> str:
        """
        Export users as CSV.

        Args:
            db: Database session
            role_id: Filter by role
            limit: Maximum number of records

        Returns:
            CSV string
        """
        stmt = select(User).options(joinedload(User.role))

        if role_id:
            stmt = stmt.where(User.role_id == role_id)
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        users = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(["ID", "Username", "Email", "Role"])

        # Write data
        for user in users:
            writer.writerow(
                [
                    user.id,
                    user.username,
                    user.email,
                    user.role.name,
                ]
            )

        return output.getvalue()

    @staticmethod
    async def export_activity_logs_json(
        db: AsyncSession,
        user_id: int | None = None,
        action: str | None = None,
        limit: int = 1000,
    ) -> str:
        """
        Export activity logs as JSON.

        Args:
            db: Database session
            user_id: Filter by user
            action: Filter by action
            limit: Maximum number of records (default: 1000)

        Returns:
            JSON string
        """
        stmt = select(ActivityLog).options(joinedload(ActivityLog.user)).order_by(ActivityLog.timestamp.desc())

        if user_id:
            stmt = stmt.where(ActivityLog.user_id == user_id)
        if action:
            stmt = stmt.where(ActivityLog.action == action)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        logs = result.unique().scalars().all()

        # Convert to dict
        export_data = []
        for log in logs:
            export_data.append(
                {
                    "id": log.id,
                    "action": log.action,
                    "description": log.description,
                    "user": {
                        "id": log.user.id,
                        "username": log.user.username,
                    }
                    if log.user
                    else None,
                    "content_id": log.content_id,
                    "target_user_id": log.target_user_id,
                    "timestamp": log.timestamp.isoformat(),
                }
            )

        return json.dumps(export_data, indent=2)

    @staticmethod
    async def export_activity_logs_csv(
        db: AsyncSession,
        user_id: int | None = None,
        action: str | None = None,
        limit: int = 1000,
    ) -> str:
        """
        Export activity logs as CSV.

        Args:
            db: Database session
            user_id: Filter by user
            action: Filter by action
            limit: Maximum number of records (default: 1000)

        Returns:
            CSV string
        """
        stmt = select(ActivityLog).options(joinedload(ActivityLog.user)).order_by(ActivityLog.timestamp.desc())

        if user_id:
            stmt = stmt.where(ActivityLog.user_id == user_id)
        if action:
            stmt = stmt.where(ActivityLog.action == action)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        logs = result.unique().scalars().all()

        # Create CSV
        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "ID",
                "Action",
                "Description",
                "User ID",
                "Username",
                "Content ID",
                "Target User ID",
                "Timestamp",
            ]
        )

        # Write data
        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.action,
                    log.description,
                    log.user_id if log.user else "",
                    log.user.username if log.user else "",
                    log.content_id or "",
                    log.target_user_id or "",
                    log.timestamp.isoformat(),
                ]
            )

        return output.getvalue()


# Singleton instance
export_service = ExportService()
