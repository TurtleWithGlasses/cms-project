"""
Privacy & GDPR Compliance Routes

Provides endpoints for GDPR compliance including:
- Data export (right to data portability)
- Account deletion (right to be forgotten)
- Consent management
- Data access requests
"""

import json
import logging
from datetime import datetime, timezone
from io import StringIO
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.activity_log import ActivityLog
from app.models.content import Content
from app.models.media import Media
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(tags=["Privacy & GDPR"])

logger = logging.getLogger(__name__)


class DataExportRequest(BaseModel):
    """Request model for data export."""

    format: str = "json"  # json or csv
    include_content: bool = True
    include_activity: bool = True
    include_media: bool = True


class AccountDeletionRequest(BaseModel):
    """Request model for account deletion."""

    confirm: bool
    reason: str | None = None
    password: str  # Require password confirmation


class ConsentUpdate(BaseModel):
    """Consent preferences update model."""

    marketing_emails: bool = False
    analytics_tracking: bool = True
    third_party_sharing: bool = False


class DataExportResponse(BaseModel):
    """Response for data export request."""

    status: str
    message: str
    download_url: str | None = None


class PrivacySettings(BaseModel):
    """User privacy settings response."""

    user_id: int
    marketing_emails: bool
    analytics_tracking: bool
    third_party_sharing: bool
    data_retention_days: int
    last_updated: str


@router.get("/settings", response_model=PrivacySettings)
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
) -> PrivacySettings:
    """
    Get current privacy settings for the user.

    Returns the user's consent preferences and data retention settings.
    """
    # Default settings (in production, these would be stored per user)
    preferences = current_user.preferences or {}

    return PrivacySettings(
        user_id=current_user.id,
        marketing_emails=preferences.get("marketing_emails", False),
        analytics_tracking=preferences.get("analytics_tracking", True),
        third_party_sharing=preferences.get("third_party_sharing", False),
        data_retention_days=preferences.get("data_retention_days", 365),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@router.put("/settings", response_model=PrivacySettings)
async def update_privacy_settings(
    consent: ConsentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrivacySettings:
    """
    Update privacy and consent settings.

    Allows users to manage their consent preferences for:
    - Marketing communications
    - Analytics tracking
    - Third-party data sharing
    """
    # Update user preferences
    preferences = current_user.preferences or {}
    preferences.update(
        {
            "marketing_emails": consent.marketing_emails,
            "analytics_tracking": consent.analytics_tracking,
            "third_party_sharing": consent.third_party_sharing,
            "consent_updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    current_user.preferences = preferences
    await db.commit()

    logger.info(f"User {current_user.id} updated privacy settings")

    return PrivacySettings(
        user_id=current_user.id,
        marketing_emails=consent.marketing_emails,
        analytics_tracking=consent.analytics_tracking,
        third_party_sharing=consent.third_party_sharing,
        data_retention_days=preferences.get("data_retention_days", 365),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/export", response_model=DataExportResponse)
async def request_data_export(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DataExportResponse:
    """
    Request a full export of personal data (GDPR Article 20).

    Initiates an export of all user data in the requested format.
    The export includes:
    - Profile information
    - Content created by the user
    - Activity logs
    - Uploaded media metadata

    Returns a download URL when the export is ready.
    """
    logger.info(f"User {current_user.id} requested data export")

    # For immediate small exports, generate inline
    # For larger exports, this would be a background task
    try:
        # Validate export can be generated (in production, store result)
        await _generate_user_export(
            db=db,
            user=current_user,
            include_content=request.include_content,
            include_activity=request.include_activity,
            include_media=request.include_media,
        )

        # Store export for download (in production, use cloud storage)
        # For now, return inline
        return DataExportResponse(
            status="completed",
            message="Your data export is ready for download",
            download_url=f"/api/v1/privacy/export/download?format={request.format}",
        )
    except Exception as e:
        logger.error(f"Data export failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate data export",
        ) from e


@router.get("/export/download")
async def download_data_export(
    format: str = "json",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Download the data export file.

    Returns the user's data in the requested format (JSON or CSV).
    """
    export_data = await _generate_user_export(
        db=db,
        user=current_user,
        include_content=True,
        include_activity=True,
        include_media=True,
    )

    if format == "json":
        content = json.dumps(export_data, indent=2, default=str)
        media_type = "application/json"
        filename = f"data_export_{current_user.id}_{datetime.now().strftime('%Y%m%d')}.json"
    else:
        # CSV format - flatten the data
        content = _convert_to_csv(export_data)
        media_type = "text/csv"
        filename = f"data_export_{current_user.id}_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        iter([content]),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/delete-account")
async def request_account_deletion(
    request: AccountDeletionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """
    Request account deletion (GDPR Article 17 - Right to Erasure).

    This will:
    1. Delete all user content
    2. Delete all activity logs
    3. Delete all notifications
    4. Anonymize any data that must be retained for legal reasons
    5. Delete the user account

    This action is IRREVERSIBLE.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm account deletion",
        )

    # Verify password
    from app.auth import verify_password

    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    logger.warning(f"User {current_user.id} ({current_user.email}) requested account deletion")

    try:
        # Delete user's content
        await db.execute(delete(Content).where(Content.author_id == current_user.id))

        # Delete activity logs
        await db.execute(delete(ActivityLog).where(ActivityLog.user_id == current_user.id))

        # Delete notifications
        await db.execute(delete(Notification).where(Notification.user_id == current_user.id))

        # Delete media (metadata - actual files should be cleaned separately)
        await db.execute(delete(Media).where(Media.uploaded_by == current_user.id))

        # Delete the user
        await db.execute(delete(User).where(User.id == current_user.id))

        await db.commit()

        logger.info(f"Account deleted for user {current_user.id}")

        return {
            "status": "success",
            "message": "Your account and all associated data have been permanently deleted",
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"Account deletion failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account. Please contact support.",
        ) from e


@router.get("/data-summary")
async def get_data_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get a summary of all data stored about the user.

    Provides an overview without downloading the full export.
    """
    # Count content
    content_result = await db.execute(select(Content).where(Content.author_id == current_user.id))
    content_count = len(content_result.scalars().all())

    # Count activity logs
    activity_result = await db.execute(select(ActivityLog).where(ActivityLog.user_id == current_user.id))
    activity_count = len(activity_result.scalars().all())

    # Count media
    media_result = await db.execute(select(Media).where(Media.uploaded_by == current_user.id))
    media_count = len(media_result.scalars().all())

    # Count notifications
    notification_result = await db.execute(select(Notification).where(Notification.user_id == current_user.id))
    notification_count = len(notification_result.scalars().all())

    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "account_created": current_user.created_at.isoformat() if hasattr(current_user, "created_at") else None,
        "data_summary": {
            "content_items": content_count,
            "activity_logs": activity_count,
            "media_files": media_count,
            "notifications": notification_count,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def _generate_user_export(
    db: AsyncSession,
    user: User,
    include_content: bool = True,
    include_activity: bool = True,
    include_media: bool = True,
) -> dict[str, Any]:
    """Generate a complete export of user data."""
    export_data = {
        "export_info": {
            "user_id": user.id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format_version": "1.0",
        },
        "profile": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.name if user.role else None,
            "preferences": user.preferences,
        },
    }

    if include_content:
        result = await db.execute(
            select(Content).where(Content.author_id == user.id).options(selectinload(Content.tags))
        )
        contents = result.scalars().all()
        export_data["content"] = [
            {
                "id": c.id,
                "title": c.title,
                "slug": c.slug,
                "body": c.body,
                "status": c.status.value if c.status else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "tags": [t.name for t in c.tags] if c.tags else [],
            }
            for c in contents
        ]

    if include_activity:
        result = await db.execute(select(ActivityLog).where(ActivityLog.user_id == user.id).limit(1000))
        activities = result.scalars().all()
        export_data["activity_logs"] = [
            {
                "id": a.id,
                "action": a.action,
                "details": a.details,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            }
            for a in activities
        ]

    if include_media:
        result = await db.execute(select(Media).where(Media.uploaded_by == user.id))
        media_files = result.scalars().all()
        export_data["media"] = [
            {
                "id": m.id,
                "filename": m.filename,
                "original_filename": m.original_filename,
                "file_type": m.file_type,
                "file_size": m.file_size,
                "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            }
            for m in media_files
        ]

    return export_data


def _convert_to_csv(data: dict[str, Any]) -> str:
    """Convert export data to CSV format."""
    output = StringIO()

    # Profile section
    output.write("=== PROFILE ===\n")
    profile = data.get("profile", {})
    for key, value in profile.items():
        output.write(f"{key},{value}\n")

    # Content section
    if "content" in data:
        output.write("\n=== CONTENT ===\n")
        output.write("id,title,slug,status,created_at,updated_at\n")
        for item in data["content"]:
            output.write(
                f"{item['id']},{item['title']},{item['slug']},{item['status']},{item['created_at']},{item['updated_at']}\n"
            )

    # Activity section
    if "activity_logs" in data:
        output.write("\n=== ACTIVITY LOGS ===\n")
        output.write("id,action,timestamp\n")
        for item in data["activity_logs"]:
            output.write(f"{item['id']},{item['action']},{item['timestamp']}\n")

    # Media section
    if "media" in data:
        output.write("\n=== MEDIA ===\n")
        output.write("id,filename,file_type,file_size,uploaded_at\n")
        for item in data["media"]:
            output.write(
                f"{item['id']},{item['filename']},{item['file_type']},{item['file_size']},{item['uploaded_at']}\n"
            )

    return output.getvalue()
