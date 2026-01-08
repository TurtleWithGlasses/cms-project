from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationStatus(str, PyEnum):
    UNREAD = "UNREAD"
    READ = "READ"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content.id"), index=True)
    message = Column(String, nullable=False)
    status: Column[NotificationStatus] = Column(
        Enum(NotificationStatus), default=NotificationStatus.UNREAD, nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship(
        "User", back_populates="notifications", cascade="all, delete-orphan", single_parent=True, lazy="selectin"
    )
    content = relationship(
        "Content", back_populates="notifications", cascade="all, delete-orphan", single_parent=True, lazy="selectin"
    )
