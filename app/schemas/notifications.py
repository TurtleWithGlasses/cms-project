from pydantic import BaseModel
from datetime import datetime
from typing import List
from app.models.notification import NotificationStatus


class NotificationOut(BaseModel):
    id: int
    content_id: int
    user_id: int
    message: str
    status: NotificationStatus
    created_at: datetime

    class Config:
        from_attributes = True  # Ensures compatibility with ORM models


class PaginatedNotifications(BaseModel):
    total: int  # Total number of notifications available
    page: int  # Current page number
    size: int  # Number of notifications per page
    notifications: List[NotificationOut]  # List of notifications for the current page

    class Config:
        schema_extra = {
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


class MarkAllNotificationsReadRequest(BaseModel):
    unread_notification_ids: List[int]  # List of notification IDs to mark as read

    class Config:
        schema_extra = {
            "example": {
                "unread_notification_ids": [1, 2, 3, 4],
            }
        }
