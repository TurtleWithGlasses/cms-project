from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from app.models.content_tags import content_tags  # Ensure content_tags is properly defined
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
    publish_date = Column(DateTime, nullable=True)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(String, nullable=True)

    # Unique constraint for slug
    __table_args__ = (UniqueConstraint("slug", name="unique_slug"),)

    # Relationships
    author = relationship("User", back_populates="contents")  # Ensure User model has `contents`
    activity_logs = relationship("ActivityLog", back_populates="content")  # Ensure ActivityLog model has `content`
    tags = relationship("Tag", secondary=content_tags, back_populates="contents")  # Ensure `Tag` model has `contents`
