"""
Analytics Service

Provides analytics and reporting for content, users, and system activity.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.activity_log import ActivityLog
from app.models.content import Content
from app.models.media import Media
from app.models.user import User


class AnalyticsService:
    """Service for generating analytics and reports"""

    @staticmethod
    async def get_content_statistics(db: AsyncSession) -> dict[str, Any]:
        """
        Get overall content statistics.

        Args:
            db: Database session

        Returns:
            Dict with content statistics
        """
        # Total content count
        total_result = await db.execute(select(func.count(Content.id)))
        total_content = total_result.scalar()

        # Content by status
        status_result = await db.execute(select(Content.status, func.count(Content.id)).group_by(Content.status))
        content_by_status = {status.value: count for status, count in status_result.all()}

        # Content created in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_result = await db.execute(select(func.count(Content.id)).where(Content.created_at >= thirty_days_ago))
        recent_content = recent_result.scalar()

        # Content by category (top 10)
        category_result = await db.execute(
            select(func.coalesce(Content.category_id, 0).label("category_id"), func.count(Content.id).label("count"))
            .group_by("category_id")
            .order_by(func.count(Content.id).desc())
            .limit(10)
        )
        content_by_category = [{"category_id": cat_id, "count": count} for cat_id, count in category_result.all()]

        return {
            "total_content": total_content,
            "content_by_status": content_by_status,
            "recent_content_30_days": recent_content,
            "content_by_category_top10": content_by_category,
        }

    @staticmethod
    async def get_user_statistics(db: AsyncSession) -> dict[str, Any]:
        """
        Get user statistics.

        Args:
            db: Database session

        Returns:
            Dict with user statistics
        """
        # Total users
        total_result = await db.execute(select(func.count(User.id)))
        total_users = total_result.scalar()

        # Users by role
        role_result = await db.execute(select(User.role_id, func.count(User.id)).group_by(User.role_id))
        users_by_role = dict(role_result.all())

        # Most active users (by content created)
        active_users_result = await db.execute(
            select(User.id, User.username, func.count(Content.id).label("content_count"))
            .join(Content, Content.author_id == User.id)
            .group_by(User.id, User.username)
            .order_by(func.count(Content.id).desc())
            .limit(10)
        )
        most_active_users = [
            {"user_id": user_id, "username": username, "content_count": count}
            for user_id, username, count in active_users_result.all()
        ]

        return {
            "total_users": total_users,
            "users_by_role": users_by_role,
            "most_active_users_top10": most_active_users,
        }

    @staticmethod
    async def get_activity_statistics(
        db: AsyncSession,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Get activity log statistics.

        Args:
            db: Database session
            days: Number of days to analyze

        Returns:
            Dict with activity statistics
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Total activities
        total_result = await db.execute(select(func.count(ActivityLog.id)).where(ActivityLog.timestamp >= start_date))
        total_activities = total_result.scalar()

        # Activities by action type
        action_result = await db.execute(
            select(ActivityLog.action, func.count(ActivityLog.id))
            .where(ActivityLog.timestamp >= start_date)
            .group_by(ActivityLog.action)
            .order_by(func.count(ActivityLog.id).desc())
        )
        activities_by_action = dict(action_result.all())

        # Activities per day (last N days)
        daily_result = await db.execute(
            select(func.date(ActivityLog.timestamp).label("date"), func.count(ActivityLog.id).label("count"))
            .where(ActivityLog.timestamp >= start_date)
            .group_by("date")
            .order_by("date")
        )
        daily_activities = [{"date": str(date), "count": count} for date, count in daily_result.all()]

        # Most active users (by activity count)
        user_activity_result = await db.execute(
            select(User.id, User.username, func.count(ActivityLog.id).label("activity_count"))
            .join(ActivityLog, ActivityLog.user_id == User.id)
            .where(ActivityLog.timestamp >= start_date)
            .group_by(User.id, User.username)
            .order_by(func.count(ActivityLog.id).desc())
            .limit(10)
        )
        most_active_users = [
            {"user_id": user_id, "username": username, "activity_count": count}
            for user_id, username, count in user_activity_result.all()
        ]

        return {
            "period_days": days,
            "total_activities": total_activities,
            "activities_by_action": activities_by_action,
            "daily_activities": daily_activities,
            "most_active_users_top10": most_active_users,
        }

    @staticmethod
    async def get_media_statistics(db: AsyncSession) -> dict[str, Any]:
        """
        Get media upload statistics.

        Args:
            db: Database session

        Returns:
            Dict with media statistics
        """
        # Total media count
        total_result = await db.execute(select(func.count(Media.id)))
        total_media = total_result.scalar()

        # Total storage used (in bytes)
        storage_result = await db.execute(select(func.sum(Media.file_size)))
        total_storage = storage_result.scalar() or 0

        # Media by type
        type_result = await db.execute(select(Media.file_type, func.count(Media.id)).group_by(Media.file_type))
        media_by_type = dict(type_result.all())

        # Top uploaders
        uploader_result = await db.execute(
            select(
                User.id,
                User.username,
                func.count(Media.id).label("upload_count"),
                func.sum(Media.file_size).label("total_size"),
            )
            .join(Media, Media.uploaded_by == User.id)
            .group_by(User.id, User.username)
            .order_by(func.count(Media.id).desc())
            .limit(10)
        )
        top_uploaders = [
            {"user_id": user_id, "username": username, "upload_count": count, "total_size_bytes": size or 0}
            for user_id, username, count, size in uploader_result.all()
        ]

        return {
            "total_media": total_media,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
            "media_by_type": media_by_type,
            "top_uploaders_top10": top_uploaders,
        }

    @staticmethod
    async def get_dashboard_overview(db: AsyncSession) -> dict[str, Any]:
        """
        Get comprehensive dashboard overview.

        Args:
            db: Database session

        Returns:
            Dict with all statistics
        """
        content_stats = await AnalyticsService.get_content_statistics(db)
        user_stats = await AnalyticsService.get_user_statistics(db)
        activity_stats = await AnalyticsService.get_activity_statistics(db, days=30)
        media_stats = await AnalyticsService.get_media_statistics(db)

        return {
            "content": content_stats,
            "users": user_stats,
            "activity": activity_stats,
            "media": media_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    async def get_user_performance_report(
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """
        Get performance report for a specific user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Dict with user performance metrics
        """
        # Get user
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalars().first()

        if not user:
            return {"error": "User not found"}

        # Content created
        content_result = await db.execute(select(func.count(Content.id)).where(Content.author_id == user_id))
        total_content = content_result.scalar()

        # Content by status
        status_result = await db.execute(
            select(Content.status, func.count(Content.id)).where(Content.author_id == user_id).group_by(Content.status)
        )
        content_by_status = {status.value: count for status, count in status_result.all()}

        # Activities
        activity_result = await db.execute(select(func.count(ActivityLog.id)).where(ActivityLog.user_id == user_id))
        total_activities = activity_result.scalar()

        # Media uploaded
        media_result = await db.execute(
            select(func.count(Media.id), func.sum(Media.file_size)).where(Media.uploaded_by == user_id)
        )
        media_count, total_storage = media_result.one()

        return {
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name,
            "content_created": total_content,
            "content_by_status": content_by_status,
            "total_activities": total_activities,
            "media_uploaded": media_count or 0,
            "storage_used_bytes": total_storage or 0,
            "storage_used_mb": round((total_storage or 0) / (1024 * 1024), 2),
        }


# Singleton instance
analytics_service = AnalyticsService()
