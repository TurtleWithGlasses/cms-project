"""Dashboard routes for KPIs, analytics, and system health."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.routes.auth import get_current_user, require_role
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Pydantic schemas
class ContentKPIsResponse(BaseModel):
    """Schema for content KPIs."""

    total_content: int
    published_content: int
    content_this_period: int
    content_previous_period: int
    growth_rate_percent: float
    content_by_status: dict
    stale_drafts: int
    period_days: int


class UserKPIsResponse(BaseModel):
    """Schema for user KPIs."""

    total_users: int
    active_users: int
    inactive_users: int
    new_users_this_period: int
    two_fa_enabled_users: int
    two_fa_adoption_percent: float
    active_sessions: int
    period_days: int


class ActivityKPIsResponse(BaseModel):
    """Schema for activity KPIs."""

    total_actions: int
    actions_by_type: dict
    most_active_users: list[dict]
    daily_activity: list[dict]
    avg_daily_actions: float
    period_days: int


class CommentKPIsResponse(BaseModel):
    """Schema for comment KPIs."""

    total_comments: int
    comments_this_period: int
    comments_by_status: dict
    pending_moderation: int
    period_days: int


class ImportKPIsResponse(BaseModel):
    """Schema for import KPIs."""

    total_imports: int
    imports_by_status: dict
    successful_records: int
    failed_records: int
    skipped_records: int
    success_rate_percent: float
    period_days: int


class DashboardSummaryResponse(BaseModel):
    """Schema for complete dashboard summary."""

    generated_at: str
    period_days: int
    content: ContentKPIsResponse
    users: UserKPIsResponse
    activity: ActivityKPIsResponse
    comments: CommentKPIsResponse
    imports: ImportKPIsResponse
    highlights: dict


class SystemHealthResponse(BaseModel):
    """Schema for system health."""

    status: str
    timestamp: str
    database: str
    metrics: dict


class ContentPerformanceResponse(BaseModel):
    """Schema for content performance."""

    id: int
    title: str
    status: str
    comment_count: int


class ActivityTimelineResponse(BaseModel):
    """Schema for activity timeline item."""

    id: int
    action: str
    resource_type: str | None
    resource_id: int | None
    details: str | None
    created_at: str


# Routes
@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive dashboard summary with all KPIs."""
    summary = await dashboard_service.get_dashboard_summary(db, period_days)
    return summary


@router.get("/kpis/content", response_model=ContentKPIsResponse)
async def get_content_kpis(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Get content-related KPIs."""
    return await dashboard_service.get_content_kpis(db, period_days)


@router.get("/kpis/users", response_model=UserKPIsResponse)
async def get_user_kpis(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get user-related KPIs. Admin only."""
    return await dashboard_service.get_user_kpis(db, period_days)


@router.get("/kpis/activity", response_model=ActivityKPIsResponse)
async def get_activity_kpis(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get activity-related KPIs. Admin only."""
    return await dashboard_service.get_activity_kpis(db, period_days)


@router.get("/kpis/comments", response_model=CommentKPIsResponse)
async def get_comment_kpis(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Get comment-related KPIs."""
    return await dashboard_service.get_comment_kpis(db, period_days)


@router.get("/kpis/imports", response_model=ImportKPIsResponse)
async def get_import_kpis(
    period_days: int = 30,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get import-related KPIs. Admin only."""
    return await dashboard_service.get_import_kpis(db, period_days)


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health(
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get system health metrics. Admin only."""
    return await dashboard_service.get_system_health(db)


@router.get("/content-performance", response_model=list[ContentPerformanceResponse])
async def get_content_performance(
    period_days: int = 30,
    limit: int = 10,
    current_user: User = Depends(require_role(["admin", "editor"])),
    db: AsyncSession = Depends(get_db),
):
    """Get top performing content based on engagement."""
    return await dashboard_service.get_content_performance(db, period_days, limit)


@router.get("/my-activity", response_model=list[ActivityTimelineResponse])
async def get_my_activity(
    period_days: int = 7,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity timeline for the current user."""
    return await dashboard_service.get_user_activity_timeline(db, current_user.id, period_days)


@router.get("/user/{user_id}/activity", response_model=list[ActivityTimelineResponse])
async def get_user_activity(
    user_id: int,
    period_days: int = 7,
    current_user: User = Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db),
):
    """Get activity timeline for a specific user. Admin only."""
    return await dashboard_service.get_user_activity_timeline(db, user_id, period_days)
