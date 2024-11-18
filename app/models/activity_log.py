from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content_id = Column(Integer, ForeignKey("content.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    description = Column(Text, nullable=False)
    details = Column(Text, nullable=True)

    user = relationship("User", back_populates="activity_logs", foreign_keys=[user_id])
    target_user = relationship("User", back_populates="target_activity_logs", foreign_keys=[target_user_id])
    content = relationship("Content", back_populates="activity_logs")
