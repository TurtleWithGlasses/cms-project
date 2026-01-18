"""
Notification Routes

API endpoints for notification management and user preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.notification_preference import DigestFrequency, NotificationCategory
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ============== Schemas ==============


class NotificationResponse(BaseModel):
    """Response for a notification."""

    id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: str


class PreferenceUpdate(BaseModel):
    """Request to update notification preference."""

    email_enabled: bool | None = None
    in_app_enabled: bool | None = None
    push_enabled: bool | None = None
    sms_enabled: bool | None = None
    digest_frequency: str | None = None
    quiet_hours: str | None = None


class PreferenceResponse(BaseModel):
    """Response for notification preference."""

    category: str
    email_enabled: bool
    in_app_enabled: bool
    push_enabled: bool
    sms_enabled: bool
    digest_frequency: str
    quiet_hours: str | None


class TemplateCreate(BaseModel):
    """Request to create a notification template."""

    name: str = Field(..., min_length=1, max_length=100)
    category: str
    subject: str = Field(..., min_length=1, max_length=255)
    body_text: str = Field(..., min_length=1)
    body_html: str | None = None
    description: str | None = None
    push_title: str | None = Field(None, max_length=100)
    push_body: str | None = Field(None, max_length=255)
    variables: list[str] | None = None


class TemplateResponse(BaseModel):
    """Response for notification template."""

    id: int
    name: str
    description: str | None
    category: str
    subject: str
    variables: list[str]


class SendNotificationRequest(BaseModel):
    """Request to send a notification."""

    user_id: int
    category: str
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    template_name: str | None = None
    variables: dict | None = None


# ============== User Notifications ==============


@router.get("", response_model=list[NotificationResponse])
async def get_my_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationResponse]:
    """
    Get notifications for the current user.
    """
    service = NotificationService(db)
    notifications = await service.get_user_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )
    return [NotificationResponse(**n) for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get count of unread notifications.
    """
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Mark a notification as read.
    """
    service = NotificationService(db)
    success = await service.mark_as_read(current_user.id, notification_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return {"success": True, "message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Mark all notifications as read.
    """
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return {"marked_read": count, "message": f"{count} notifications marked as read"}


# ============== Preferences ==============


@router.get("/preferences", response_model=list[PreferenceResponse])
async def get_my_preferences(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PreferenceResponse]:
    """
    Get notification preferences for the current user.

    Returns preferences for all categories.
    """
    service = NotificationService(db)
    prefs = await service.get_user_preferences(current_user.id)
    return [PreferenceResponse(**p) for p in prefs]


@router.put("/preferences/{category}", response_model=PreferenceResponse)
async def update_preference(
    category: str,
    data: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PreferenceResponse:
    """
    Update notification preference for a category.
    """
    service = NotificationService(db)

    try:
        result = await service.update_preference(
            user_id=current_user.id,
            category=category,
            email_enabled=data.email_enabled,
            in_app_enabled=data.in_app_enabled,
            push_enabled=data.push_enabled,
            sms_enabled=data.sms_enabled,
            digest_frequency=data.digest_frequency,
            quiet_hours=data.quiet_hours,
        )
        return PreferenceResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/categories")
async def list_notification_categories() -> dict:
    """
    List available notification categories.
    """
    return {"categories": [{"value": cat.value, "name": cat.name} for cat in NotificationCategory]}


@router.get("/digest-frequencies")
async def list_digest_frequencies() -> dict:
    """
    List available digest frequencies.
    """
    return {"frequencies": [{"value": freq.value, "name": freq.name} for freq in DigestFrequency]}


# ============== Templates (Admin) ==============


@router.get("/templates", response_model=list[TemplateResponse])
async def list_templates(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TemplateResponse]:
    """
    List notification templates.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    service = NotificationService(db)
    templates = await service.get_templates(category)
    return [TemplateResponse(**t) for t in templates]


@router.post("/templates", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Create a notification template.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    service = NotificationService(db)

    try:
        result = await service.create_template(
            name=data.name,
            category=data.category,
            subject=data.subject,
            body_text=data.body_text,
            body_html=data.body_html,
            description=data.description,
            push_title=data.push_title,
            push_body=data.push_body,
            variables=data.variables,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# ============== Send Notification (Admin) ==============


@router.post("/send")
async def send_notification(
    data: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Send a notification to a user.

    Admin endpoint for sending system notifications.
    """
    if not current_user.role or current_user.role.name not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    service = NotificationService(db)

    try:
        result = await service.send_notification(
            user_id=data.user_id,
            category=data.category,
            subject=data.subject,
            body=data.body,
            template_name=data.template_name,
            variables=data.variables,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
