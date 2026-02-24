import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.content_tags import content_tags


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
    status: Column[ContentStatus] = Column(Enum(ContentStatus), default=ContentStatus.DRAFT, nullable=False)
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

    # Full-text search vector (populated by PostgreSQL trigger)
    search_vector = Column(TSVECTOR, nullable=True)

    # Relationships
    notifications = relationship("Notification", back_populates="content", cascade="all, delete-orphan")
    author = relationship("User", back_populates="contents", lazy="selectin")
    activity_logs = relationship("ActivityLog", back_populates="content", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=content_tags, back_populates="contents")

    # Comment relationship
    comments = relationship("Comment", back_populates="content", cascade="all, delete-orphan", lazy="selectin")

    # View tracking
    views = relationship("ContentView", back_populates="content", cascade="all, delete-orphan", lazy="noload")

    # i18n: per-locale translations (Phase 6.3)
    translations = relationship(
        "ContentTranslation",
        back_populates="content",
        cascade="all, delete-orphan",
        lazy="noload",  # never eager-loaded; use explicit joins in translation queries
    )

    # Unique constraint for slug and performance indexes
    __table_args__ = (
        UniqueConstraint("slug", name="unique_slug"),
        Index("idx_content_status", "status"),
        Index("ix_content_category_id", "category_id"),
        Index("ix_content_created_at", "created_at"),
        Index("ix_content_updated_at", "updated_at"),
        Index("ix_content_publish_date", "publish_date"),
        Index("ix_content_status_created", "status", "created_at"),
        Index("ix_content_search_vector", "search_vector", postgresql_using="gin"),
    )
