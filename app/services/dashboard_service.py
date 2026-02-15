"""Dashboard service for KPIs, analytics, and real-time metrics."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.comment import Comment, CommentStatus
from app.models.content import Content
from app.models.content_view import ContentView
from app.models.import_job import ImportJob, ImportStatus
from app.models.user import User
from app.models.user_session import UserSession


async def get_content_kpis(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get content-related KPIs using batched conditional aggregation."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)
    previous_start = period_start - timedelta(days=period_days)
    stale_threshold = now - timedelta(days=7)

    # Single query: total, published, this_period, prev_period, stale_drafts
    agg_result = await db.execute(
        select(
            func.count(Content.id).label("total"),
            func.count(Content.id).filter(Content.status == "published").label("published"),
            func.count(Content.id).filter(Content.created_at >= period_start).label("this_period"),
            func.count(Content.id)
            .filter(Content.created_at >= previous_start, Content.created_at < period_start)
            .label("prev_period"),
            func.count(Content.id)
            .filter(Content.status == "draft", Content.created_at < stale_threshold)
            .label("stale_drafts"),
        )
    )
    row = agg_result.one()
    total_content = row.total or 0
    published_content = row.published or 0
    content_this_period = row.this_period or 0
    content_previous_period = row.prev_period or 0
    stale_drafts = row.stale_drafts or 0

    # Growth rate
    growth_rate = 0.0
    if content_previous_period > 0:
        growth_rate = (content_this_period - content_previous_period) / content_previous_period * 100

    # Content by status (separate GROUP BY query)
    status_result = await db.execute(select(Content.status, func.count(Content.id)).group_by(Content.status))
    content_by_status = {row[0]: row[1] for row in status_result.fetchall()}

    return {
        "total_content": total_content,
        "published_content": published_content,
        "content_this_period": content_this_period,
        "content_previous_period": content_previous_period,
        "growth_rate_percent": round(growth_rate, 2),
        "content_by_status": content_by_status,
        "stale_drafts": stale_drafts,
        "period_days": period_days,
    }


async def get_user_kpis(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get user-related KPIs using batched conditional aggregation."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)

    # Single query: total, active, new, 2fa
    agg_result = await db.execute(
        select(
            func.count(User.id).label("total"),
            func.count(User.id).filter(User.is_active.is_(True)).label("active"),
            func.count(User.id).filter(User.created_at >= period_start).label("new"),
            func.count(User.id).filter(User.two_factor_enabled.is_(True)).label("two_fa"),
        )
    )
    row = agg_result.one()
    total_users = row.total or 0
    active_users = row.active or 0
    new_users = row.new or 0
    two_fa_users = row.two_fa or 0

    # Active sessions (different table, separate query)
    active_sessions_result = await db.execute(
        select(func.count(UserSession.id)).where(UserSession.is_active.is_(True)).where(UserSession.expires_at > now)
    )
    active_sessions = active_sessions_result.scalar() or 0

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": total_users - active_users,
        "new_users_this_period": new_users,
        "two_fa_enabled_users": two_fa_users,
        "two_fa_adoption_percent": round((two_fa_users / total_users * 100) if total_users > 0 else 0, 2),
        "active_sessions": active_sessions,
        "period_days": period_days,
    }


async def get_activity_kpis(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get activity-related KPIs."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)

    # Total actions in period
    total_result = await db.execute(select(func.count(ActivityLog.id)).where(ActivityLog.timestamp >= period_start))
    total_actions = total_result.scalar() or 0

    # Actions by type
    actions_by_type_result = await db.execute(
        select(ActivityLog.action, func.count(ActivityLog.id))
        .where(ActivityLog.timestamp >= period_start)
        .group_by(ActivityLog.action)
        .order_by(func.count(ActivityLog.id).desc())
        .limit(10)
    )
    actions_by_type = {row[0]: row[1] for row in actions_by_type_result.fetchall()}

    # Most active users
    active_users_result = await db.execute(
        select(ActivityLog.user_id, func.count(ActivityLog.id))
        .where(ActivityLog.timestamp >= period_start)
        .where(ActivityLog.user_id.isnot(None))
        .group_by(ActivityLog.user_id)
        .order_by(func.count(ActivityLog.id).desc())
        .limit(5)
    )
    most_active_users = [{"user_id": row[0], "action_count": row[1]} for row in active_users_result.fetchall()]

    # Daily activity breakdown
    daily_result = await db.execute(
        select(
            func.date(ActivityLog.timestamp).label("date"),
            func.count(ActivityLog.id),
        )
        .where(ActivityLog.timestamp >= period_start)
        .group_by(func.date(ActivityLog.timestamp))
        .order_by(func.date(ActivityLog.timestamp))
    )
    daily_activity = [{"date": str(row[0]), "count": row[1]} for row in daily_result.fetchall()]

    return {
        "total_actions": total_actions,
        "actions_by_type": actions_by_type,
        "most_active_users": most_active_users,
        "daily_activity": daily_activity,
        "avg_daily_actions": round(total_actions / period_days, 2) if period_days > 0 else 0,
        "period_days": period_days,
    }


async def get_comment_kpis(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get comment-related KPIs."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)

    # Total comments
    total_result = await db.execute(select(func.count(Comment.id)))
    total_comments = total_result.scalar() or 0

    # Comments in period
    period_result = await db.execute(select(func.count(Comment.id)).where(Comment.created_at >= period_start))
    comments_this_period = period_result.scalar() or 0

    # Comments by status
    status_result = await db.execute(select(Comment.status, func.count(Comment.id)).group_by(Comment.status))
    comments_by_status = {row[0].value: row[1] for row in status_result.fetchall()}

    # Pending moderation
    pending_result = await db.execute(select(func.count(Comment.id)).where(Comment.status == CommentStatus.PENDING))
    pending_moderation = pending_result.scalar() or 0

    return {
        "total_comments": total_comments,
        "comments_this_period": comments_this_period,
        "comments_by_status": comments_by_status,
        "pending_moderation": pending_moderation,
        "period_days": period_days,
    }


async def get_import_kpis(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get import-related KPIs."""
    now = datetime.utcnow()
    period_start = now - timedelta(days=period_days)

    # Total imports in period
    total_result = await db.execute(select(func.count(ImportJob.id)).where(ImportJob.created_at >= period_start))
    total_imports = total_result.scalar() or 0

    # Imports by status
    status_result = await db.execute(
        select(ImportJob.status, func.count(ImportJob.id))
        .where(ImportJob.created_at >= period_start)
        .group_by(ImportJob.status)
    )
    imports_by_status = {row[0].value: row[1] for row in status_result.fetchall()}

    # Total records processed
    records_result = await db.execute(
        select(
            func.sum(ImportJob.successful_records),
            func.sum(ImportJob.failed_records),
            func.sum(ImportJob.skipped_records),
        ).where(ImportJob.created_at >= period_start)
    )
    records_row = records_result.fetchone()
    successful = records_row[0] or 0
    failed = records_row[1] or 0
    skipped = records_row[2] or 0

    return {
        "total_imports": total_imports,
        "imports_by_status": imports_by_status,
        "successful_records": successful,
        "failed_records": failed,
        "skipped_records": skipped,
        "success_rate_percent": round(
            (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0,
            2,
        ),
        "period_days": period_days,
    }


async def get_dashboard_summary(
    db: AsyncSession,
    period_days: int = 30,
) -> dict:
    """Get comprehensive dashboard summary with all KPIs."""
    content_kpis = await get_content_kpis(db, period_days)
    user_kpis = await get_user_kpis(db, period_days)
    activity_kpis = await get_activity_kpis(db, period_days)
    comment_kpis = await get_comment_kpis(db, period_days)
    import_kpis = await get_import_kpis(db, period_days)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "period_days": period_days,
        "content": content_kpis,
        "users": user_kpis,
        "activity": activity_kpis,
        "comments": comment_kpis,
        "imports": import_kpis,
        "highlights": {
            "total_content": content_kpis["total_content"],
            "published_content": content_kpis["published_content"],
            "total_users": user_kpis["total_users"],
            "active_sessions": user_kpis["active_sessions"],
            "pending_moderation": comment_kpis["pending_moderation"],
            "content_growth_rate": content_kpis["growth_rate_percent"],
        },
    }


async def get_system_health(db: AsyncSession) -> dict:
    """Get system health metrics."""
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)

    # Database connectivity
    try:
        await db.execute(select(func.count(User.id)))
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {e!s}"

    # Recent activity (indicator of system usage)
    activity_result = await db.execute(select(func.count(ActivityLog.id)).where(ActivityLog.timestamp >= one_hour_ago))
    recent_activity = activity_result.scalar() or 0

    # Active sessions
    sessions_result = await db.execute(
        select(func.count(UserSession.id)).where(UserSession.is_active.is_(True)).where(UserSession.expires_at > now)
    )
    active_sessions = sessions_result.scalar() or 0

    # Pending imports
    pending_imports_result = await db.execute(
        select(func.count(ImportJob.id)).where(ImportJob.status.in_([ImportStatus.PENDING, ImportStatus.PROCESSING]))
    )
    pending_imports = pending_imports_result.scalar() or 0

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": now.isoformat(),
        "database": db_status,
        "metrics": {
            "active_sessions": active_sessions,
            "activity_last_hour": recent_activity,
            "pending_imports": pending_imports,
        },
    }


async def get_user_activity_timeline(
    db: AsyncSession,
    user_id: int,
    period_days: int = 7,
) -> list[dict]:
    """Get activity timeline for a specific user."""
    period_start = datetime.utcnow() - timedelta(days=period_days)

    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.user_id == user_id)
        .where(ActivityLog.timestamp >= period_start)
        .order_by(ActivityLog.timestamp.desc())
        .limit(100)
    )

    return [
        {
            "id": log.id,
            "action": log.action,
            "content_id": log.content_id,
            "details": log.details,
            "timestamp": log.timestamp.isoformat(),
        }
        for log in result.scalars().all()
    ]


async def get_content_performance(
    db: AsyncSession,
    period_days: int = 30,
    limit: int = 10,
) -> list[dict]:
    """Get top performing content based on engagement (comments + views)."""
    period_start = datetime.utcnow() - timedelta(days=period_days)

    # Subquery for view counts
    view_subq = (
        select(
            ContentView.content_id,
            func.count(ContentView.id).label("view_count"),
        )
        .where(ContentView.created_at >= period_start)
        .group_by(ContentView.content_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Content.id,
            Content.title,
            Content.status,
            func.count(Comment.id).label("comment_count"),
            func.coalesce(view_subq.c.view_count, 0).label("view_count"),
        )
        .outerjoin(Comment, Content.id == Comment.content_id)
        .outerjoin(view_subq, Content.id == view_subq.c.content_id)
        .where(Content.status == "published")
        .group_by(Content.id, view_subq.c.view_count)
        .order_by((func.count(Comment.id) + func.coalesce(view_subq.c.view_count, 0)).desc())
        .limit(limit)
    )

    return [
        {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "comment_count": row[3],
            "view_count": row[4],
        }
        for row in result.fetchall()
    ]
