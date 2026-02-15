"""Content view tracking model for analytics."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ContentView(Base):
    __tablename__ = "content_views"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    referrer = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    content = relationship("Content", back_populates="views")
    user = relationship("User", lazy="selectin")

    __table_args__ = (
        Index("idx_content_views_content_created", "content_id", "created_at"),
        Index("idx_content_views_dedup", "content_id", "user_id", "ip_address", "created_at"),
    )
