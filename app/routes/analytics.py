"""
Analytics Routes

API endpoints for analytics and reporting.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, get_current_user_with_role
from app.constants.roles import RoleEnum
from app.database import get_db
from app.models.user import User
from app.services.analytics_service import analytics_service

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
