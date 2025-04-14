from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from app.models.user import User


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    meta_title = Column(Text)
    meta_description = Column(Text)
    meta_keywords = Column(Text)
    slug = Column(String, nullable=True)
    status = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow)
    update_at = Column(DateTime, default=datetime.utcnow)
    
    content = relationship("Content", back_populates="versions")
    editor_id = Column(Integer, ForeignKey("users.id"))
    editor = relationship("User", foreign_keys=[editor_id])
    