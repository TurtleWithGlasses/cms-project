from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationStatus


class NotificationOut(BaseModel):
    id: int
    content_id: int
    user_id: int
    message: str
    status: NotificationStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)  # Ensures compatibility with ORM models


class PaginatedNotifications(BaseModel):
    total: int  # Total number of notifications available
    page: int  # Current page number
    size: int  # Number of notifications per page
    notifications: list[NotificationOut]  # List of notifications for the current page

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 100,
                "page": 1,
                "size": 10,
                "notifications": [
                    {
                        "id": 1,
                        "content_id": 42,
                        "user_id": 7,
                        "message": "Your content has been approved.",
                        "status": "UNREAD",
                        "created_at": "2024-11-22T10:15:30.000Z",
                    },
                ],
            }
        }
    )


class MarkAllNotificationsReadRequest(BaseModel):
    unread_notification_ids: list[int]  # List of notification IDs to mark as read

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "unread_notification_ids": [1, 2, 3, 4],
            }
        }
    )
