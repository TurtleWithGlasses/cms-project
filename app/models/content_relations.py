"""
Content Relations Models

Provides content relationships (related_to, depends_on, translated_from),
content series/collections with ordering, and URL redirects.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class RelationType(str, enum.Enum):
    """Types of content relationships."""

    RELATED_TO = "related_to"
    PART_OF_SERIES = "part_of_series"
    DEPENDS_ON = "depends_on"
    TRANSLATED_FROM = "translated_from"


class ContentRelation(Base):
    """Links two content items with a typed relationship."""

    __tablename__ = "content_relations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    target_content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    relation_type = Column(Enum(RelationType), default=RelationType.RELATED_TO, nullable=False)
    description = Column(String(255), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_content = relationship("Content", foreign_keys=[source_content_id])
    target_content = relationship("Content", foreign_keys=[target_content_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        UniqueConstraint(
            "source_content_id",
            "target_content_id",
            "relation_type",
            name="uq_content_relation",
        ),
        Index("ix_content_relations_source", "source_content_id", "relation_type"),
        Index("ix_content_relations_target", "target_content_id", "relation_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContentRelation(id={self.id}, "
            f"source={self.source_content_id}, "
            f"target={self.target_content_id}, "
            f"type={self.relation_type})>"
        )


class ContentSeries(Base):
    """Groups related content into ordered series/collections."""

    __tablename__ = "content_series"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    created_by = relationship("User", foreign_keys=[created_by_id])
    items = relationship(
        "ContentSeriesItem",
        back_populates="series",
        cascade="all, delete-orphan",
        order_by="ContentSeriesItem.order",
    )

    def __repr__(self) -> str:
        return f"<ContentSeries(id={self.id}, title={self.title})>"


class ContentSeriesItem(Base):
    """Junction table linking content to series with ordering."""

    __tablename__ = "content_series_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    series_id = Column(Integer, ForeignKey("content_series.id", ondelete="CASCADE"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    order = Column(Integer, default=0, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    series = relationship("ContentSeries", back_populates="items")
    content = relationship("Content")

    __table_args__ = (
        UniqueConstraint("series_id", "content_id", name="uq_series_content"),
        Index("ix_series_items_order", "series_id", "order"),
    )

    def __repr__(self) -> str:
        return f"<ContentSeriesItem(series={self.series_id}, content={self.content_id}, order={self.order})>"


class ContentRedirect(Base):
    """URL redirect for old slugs so URL changes don't break links."""

    __tablename__ = "content_redirects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    old_slug = Column(String(255), unique=True, nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)
    status_code = Column(Integer, default=301, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    content = relationship("Content")
    created_by = relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return f"<ContentRedirect(id={self.id}, old_slug={self.old_slug}, content_id={self.content_id})>"
