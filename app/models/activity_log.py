from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from ..database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    description = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="activity_logs", foreign_keys=[user_id], lazy="selectin")
    target_user = relationship(
        "User", back_populates="target_activity_logs", foreign_keys=[target_user_id], lazy="selectin"
    )
    content = relationship("Content", back_populates="activity_logs", lazy="selectin")

    # Indexes for performance optimization
    __table_args__ = (
        Index("idx_user_action_timestamp", "user_id", "action", "timestamp"),
        Index("idx_content_action_timestamp", "content_id", "action", "timestamp"),
    )
