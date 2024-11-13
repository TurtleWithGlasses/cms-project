from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from enum import Enum as PyEnum

class NotificationStatus(str, PyEnum):
    UNREAD = "UNREAD"
    READ = "READ"

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content_id = Column(Integer, ForeignKey("content.id"))
    message = Column(String, nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    content = relationship("Content")
