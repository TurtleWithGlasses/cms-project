from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime, Enum, Index
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
from app.models.content_tags import content_tags
from app.models.notification import Notification
import enum


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    PUBLISHED = "published"


class Content(Base):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, index=True, nullable=False)
    body = Column(Text, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)    
    description = Column(Text, nullable=True)
    publish_date = Column(DateTime, nullable=True)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    versions = relationship("ContentVersion", back_populates="content", cascade="all, delete-orphan")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    category = relationship("Category")
    
    # Metadata fields
    meta_title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(Text, nullable=True)

    # Relationships
    notifications = relationship(
        "Notification", back_populates="content", cascade="all, delete-orphan"
    )
    author = relationship("User", back_populates="contents", lazy="selectin")
    activity_logs = relationship("ActivityLog", back_populates="content", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=content_tags, back_populates="contents")

    # Unique constraint for slug
    __table_args__ = (
        UniqueConstraint("slug", name="unique_slug"),
        Index("idx_content_status", "status"),
    )
