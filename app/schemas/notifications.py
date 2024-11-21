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
        orm_mode = True

class PaginatedNotifications(BaseModel):
    total: int
    page: int
    size: int
    notifications: List[NotificationOut]

class MarkAllNotificationsReadRequest(BaseModel):
    unread_notification_ids: List[int]