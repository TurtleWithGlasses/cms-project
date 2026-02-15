"""
Analytics Service

Provides analytics and reporting for content, users, and system activity.
Includes Redis caching for performance optimization.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.activity_log import ActivityLog
from app.models.content import Content
from app.models.content_view import ContentView
from app.models.media import Media
from app.models.user import User
from app.models.user_session import UserSession
from app.utils.cache import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


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
        users_by_role: dict[int, int] = dict(role_result.all())

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
        activities_by_action: dict[str, int] = dict(action_result.all())

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
        media_by_type: dict[str, int] = dict(type_result.all())

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
        Get comprehensive dashboard overview with caching.

        Args:
            db: Database session

        Returns:
            Dict with all statistics
        """
        cache_key = f"{CacheManager.PREFIX_ANALYTICS}dashboard_overview"

        # Try cache first
        try:
            cm = await get_cache_manager()
            cached_data = await cm.get(cache_key)
            if cached_data is not None:
                logger.debug("Dashboard overview served from cache")
                return cached_data
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

        # Fetch fresh data
        content_stats = await AnalyticsService.get_content_statistics(db)
        user_stats = await AnalyticsService.get_user_statistics(db)
        activity_stats = await AnalyticsService.get_activity_statistics(db, days=30)
        media_stats = await AnalyticsService.get_media_statistics(db)

        result = {
            "content": content_stats,
            "users": user_stats,
            "activity": activity_stats,
            "media": media_stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache the result
        try:
            cm = await get_cache_manager()
            await cm.set(cache_key, result, CacheManager.TTL_ANALYTICS)
            logger.debug("Dashboard overview cached")
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")

        return result

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

    @staticmethod
    def estimate_read_time(body: str) -> int:
        """Estimate read time in minutes based on word count (~200 words/min)."""
        word_count = len(body.split())
        minutes = math.ceil(word_count / 200)
        return max(1, minutes)

    @staticmethod
    async def record_content_view(
        db: AsyncSession,
        content_id: int,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        referrer: str | None = None,
    ) -> bool:
        """
        Record a content view with 30-minute deduplication.

        Returns True if a new view was recorded, False if deduplicated.
        """
        dedup_window = datetime.now(timezone.utc) - timedelta(minutes=30)

        # Check for recent view by same user or IP
        dedup_conditions = [
            ContentView.content_id == content_id,
            ContentView.created_at >= dedup_window,
        ]

        if user_id:
            dedup_conditions.append(ContentView.user_id == user_id)
        elif ip_address:
            dedup_conditions.append(ContentView.ip_address == ip_address)
        else:
            # No user or IP — cannot deduplicate, just record
            pass

        if user_id or ip_address:
            existing = await db.execute(select(func.count(ContentView.id)).where(and_(*dedup_conditions)))
            if (existing.scalar() or 0) > 0:
                return False

        view = ContentView(
            content_id=content_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            created_at=datetime.now(timezone.utc),
        )
        db.add(view)
        await db.commit()
        return True

    @staticmethod
    async def get_content_view_stats(
        db: AsyncSession,
        content_id: int,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get view statistics for a specific content item."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Total views and unique visitors
        agg_result = await db.execute(
            select(
                func.count(ContentView.id).label("total_views"),
                func.count(func.distinct(func.coalesce(ContentView.user_id, ContentView.ip_address))).label(
                    "unique_visitors"
                ),
            ).where(
                and_(
                    ContentView.content_id == content_id,
                    ContentView.created_at >= start_date,
                )
            )
        )
        row = agg_result.one()

        # Views by day
        daily_result = await db.execute(
            select(
                func.date(ContentView.created_at).label("date"),
                func.count(ContentView.id).label("views"),
            )
            .where(
                and_(
                    ContentView.content_id == content_id,
                    ContentView.created_at >= start_date,
                )
            )
            .group_by(func.date(ContentView.created_at))
            .order_by(func.date(ContentView.created_at))
        )
        daily_views = [{"date": str(r[0]), "views": r[1]} for r in daily_result.all()]

        return {
            "content_id": content_id,
            "period_days": days,
            "total_views": row.total_views or 0,
            "unique_visitors": row.unique_visitors or 0,
            "daily_views": daily_views,
        }

    @staticmethod
    async def get_popular_content(
        db: AsyncSession,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get most popular content ranked by view count."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(
                Content.id,
                Content.title,
                Content.slug,
                func.count(ContentView.id).label("view_count"),
                func.count(func.distinct(func.coalesce(ContentView.user_id, ContentView.ip_address))).label(
                    "unique_visitors"
                ),
            )
            .join(ContentView, Content.id == ContentView.content_id)
            .where(ContentView.created_at >= start_date)
            .group_by(Content.id, Content.title, Content.slug)
            .order_by(func.count(ContentView.id).desc())
            .limit(limit)
        )

        return [
            {
                "id": row[0],
                "title": row[1],
                "slug": row[2],
                "view_count": row[3],
                "unique_visitors": row[4],
            }
            for row in result.all()
        ]

    @staticmethod
    async def get_session_analytics(
        db: AsyncSession,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get session analytics from UserSession data."""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)

        # Active sessions
        active_result = await db.execute(
            select(func.count(UserSession.id)).where(
                and_(
                    UserSession.is_active.is_(True),
                    UserSession.expires_at > now,
                )
            )
        )
        active_sessions = active_result.scalar() or 0

        # Total sessions in period
        total_result = await db.execute(select(func.count(UserSession.id)).where(UserSession.created_at >= start_date))
        total_sessions = total_result.scalar() or 0

        # Device type breakdown
        device_result = await db.execute(
            select(
                func.coalesce(UserSession.device_type, "unknown").label("device"),
                func.count(UserSession.id),
            )
            .where(UserSession.created_at >= start_date)
            .group_by(func.coalesce(UserSession.device_type, "unknown"))
        )
        device_breakdown = {row[0]: row[1] for row in device_result.all()}

        # Browser breakdown
        browser_result = await db.execute(
            select(
                func.coalesce(UserSession.browser, "unknown").label("browser"),
                func.count(UserSession.id),
            )
            .where(UserSession.created_at >= start_date)
            .group_by(func.coalesce(UserSession.browser, "unknown"))
            .order_by(func.count(UserSession.id).desc())
            .limit(10)
        )
        browser_breakdown = {row[0]: row[1] for row in browser_result.all()}

        return {
            "period_days": days,
            "active_sessions": active_sessions,
            "total_sessions": total_sessions,
            "device_breakdown": device_breakdown,
            "browser_breakdown": browser_breakdown,
        }


# Singleton instance
analytics_service = AnalyticsService()
