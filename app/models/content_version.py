from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class ContentVersion(Base):
    __tablename__ = "content_versions"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    slug = Column(String, nullable=True)
    update_at = Column(DateTime, default=datetime.utcnow)
    editor_id = Column(Integer, ForeignKey("users.id"))

    content = relationship("Content", back_populates="versions")
    editor = relationship("User")