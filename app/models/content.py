from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum


class ContentStatus(enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"

class Content(Base):
    __tablename__ = "content"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    body = Column(Text)
    slug = Column(String, unique=True, index=True)
    description = Column(Text, nullable=True)
    publish_date = Column(DateTime, default=None, nullable=True)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    author_id = Column(Integer, ForeignKey("users.id"))
    publish_date = Column(DateTime, nullable=True)

    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(String, nullable=True)

    __table_args__ = (UniqueConstraint("slug", name="unique_slug"),)

    author = relationship("User", back_populates="contents")
    tags = relationship("Tag", secondary="content_tags", back_populates="contents")