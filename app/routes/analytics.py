"""
Analytics Routes

API endpoints for analytics and reporting.
"""

import asyncio
import contextlib
import logging

import httpx
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_with_role
from app.config import settings
from app.constants.roles import RoleEnum
from app.database import get_db
from app.models.user import User
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Analytics"])


@router.get("/dashboard")
async def get_dashboard_overview(
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive dashboard overview with all statistics.

    **Requires**: Admin, Superadmin, or Manager role

    **Returns**: Complete analytics dashboard data including:
    - Content statistics
    - User statistics
    - Activity statistics
    - Media statistics
    """
    return await analytics_service.get_dashboard_overview(db)


@router.get("/content")
async def get_content_statistics(
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get content statistics.

    **Requires**: Admin, Superadmin, or Manager role

    **Returns**:
    - Total content count
    - Content by status breakdown
    - Recent content (last 30 days)
    - Top 10 categories by content count
    """
    return await analytics_service.get_content_statistics(db)


@router.get("/users")
async def get_user_statistics(
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user statistics.

    **Requires**: Admin or Superadmin role

    **Returns**:
    - Total user count
    - Users by role breakdown
    - Top 10 most active users (by content created)
    """
    return await analytics_service.get_user_statistics(db)


@router.get("/activity")
async def get_activity_statistics(
    days: int = 30,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get activity log statistics for a specified period.

    **Requires**: Admin, Superadmin, or Manager role

    **Parameters**:
    - days: Number of days to analyze (default: 30, max: 365)

    **Returns**:
    - Total activities in period
    - Activities by action type
    - Daily activity breakdown
    - Top 10 most active users
    """
    if days > 365:
        days = 365

    return await analytics_service.get_activity_statistics(db, days=days)


@router.get("/media")
async def get_media_statistics(
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get media upload statistics.

    **Requires**: Admin or Superadmin role

    **Returns**:
    - Total media count
    - Total storage used (bytes and MB)
    - Media by type breakdown
    - Top 10 uploaders
    """
    return await analytics_service.get_media_statistics(db)


@router.get("/user/{user_id}/performance")
async def get_user_performance_report(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance report for a specific user.

    Users can view their own performance.
    Admins can view any user's performance.

    **Parameters**:
    - user_id: User ID to get report for

    **Returns**:
    - User information
    - Content created count and status breakdown
    - Total activities
    - Media uploaded and storage used
    """
    # Check authorization
    if current_user.id != user_id and current_user.role.name not in [
        RoleEnum.ADMIN.value,
        RoleEnum.SUPERADMIN.value,
    ]:
        return {"error": "Not authorized to view this user's performance"}

    return await analytics_service.get_user_performance_report(db, user_id)


@router.get("/my-performance")
async def get_my_performance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get performance report for the current user.

    **Returns**:
    - Your content statistics
    - Your activity count
    - Your media uploads and storage usage
    """
    return await analytics_service.get_user_performance_report(db, current_user.id)


@router.get("/analytics/content/popular")
async def get_popular_content(
    days: int = 30,
    limit: int = 10,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get most popular content ranked by view count.

    **Requires**: Admin, Superadmin, or Manager role

    **Parameters**:
    - days: Analysis period in days (default: 30, max: 365)
    - limit: Maximum results (default: 10, max: 50)
    """
    if days > 365:
        days = 365
    if limit > 50:
        limit = 50

    return await analytics_service.get_popular_content(db, days=days, limit=limit)


@router.get("/analytics/content/{content_id}/views")
async def get_content_view_stats(
    content_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN, RoleEnum.MANAGER])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get view statistics for a specific content item.

    **Requires**: Admin, Superadmin, or Manager role

    **Parameters**:
    - content_id: Content ID
    - days: Analysis period in days (default: 30, max: 365)
    """
    if days > 365:
        days = 365

    return await analytics_service.get_content_view_stats(db, content_id, days=days)


@router.get("/analytics/sessions")
async def get_session_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user_with_role([RoleEnum.ADMIN, RoleEnum.SUPERADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get session analytics including device and browser breakdown.

    **Requires**: Admin or Superadmin role

    **Parameters**:
    - days: Analysis period in days (default: 30, max: 365)
    """
    if days > 365:
        days = 365

    return await analytics_service.get_session_analytics(db, days=days)


@router.get("/analytics/config")
async def get_analytics_config() -> dict:
    """Return frontend analytics configuration (GA4, Plausible). Public endpoint."""
    return {
        "google_analytics": {
            "enabled": bool(settings.google_analytics_measurement_id),
            "measurement_id": settings.google_analytics_measurement_id,
        },
        "plausible": {
            "enabled": bool(settings.plausible_domain),
            "domain": settings.plausible_domain,
            "api_url": settings.plausible_api_url,
        },
    }


@router.post("/analytics/events", status_code=202)
async def track_event(
    request: Request,
    payload: dict,
) -> dict:
    """Proxy a custom analytics event to GA4 and/or Plausible (fire-and-forget)."""
    asyncio.create_task(_forward_event(payload, request))
    return {"status": "accepted"}


async def _forward_event(payload: dict, request: Request) -> None:
    """Forward analytics event to GA4 Measurement Protocol and/or Plausible."""
    with contextlib.suppress(Exception):
        async with httpx.AsyncClient(timeout=5.0) as client:
            if settings.google_analytics_measurement_id and settings.google_analytics_api_secret:
                ga4_url = (
                    f"https://www.google-analytics.com/mp/collect"
                    f"?measurement_id={settings.google_analytics_measurement_id}"
                    f"&api_secret={settings.google_analytics_api_secret}"
                )
                with contextlib.suppress(Exception):
                    await client.post(ga4_url, json=payload)

            if settings.plausible_domain:
                plausible_url = f"{settings.plausible_api_url}/api/event"
                plausible_payload = {
                    "name": payload.get("name", "custom"),
                    "url": payload.get("url", str(request.url)),
                    "domain": settings.plausible_domain,
                    "props": payload.get("props", {}),
                }
                with contextlib.suppress(Exception):
                    await client.post(
                        plausible_url,
                        json=plausible_payload,
                        headers={
                            "User-Agent": request.headers.get("user-agent", "CMS-Server"),
                            "X-Forwarded-For": request.client.host if request.client else "127.0.0.1",
                        },
                    )
