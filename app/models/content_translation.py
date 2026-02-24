"""
ContentTranslation model — Phase 6.3 Internationalization

Stores per-locale translations for Content records using the
translation-table pattern. Each row contains all translatable
fields for one (content, locale) pair.

One canonical Content row + zero or many ContentTranslation rows.
Translation lifecycle: draft → in_review → published (independent
of the parent Content.status).
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class TranslationStatus(str, enum.Enum):
    """Lifecycle status for a content translation."""

    draft = "draft"
    in_review = "in_review"
    published = "published"


class ContentTranslation(Base):
    """Per-locale translation of a Content record.

    Columns mirror the translatable fields of Content (title, body, slug, etc.)
    plus translation-specific metadata (status, is_rtl, translator info).
    """

    __tablename__ = "content_translations"

    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(
        Integer,
        ForeignKey("content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    locale = Column(String(10), nullable=False, index=True)  # BCP 47 e.g. "en", "fr-CA"

    # ── Translatable fields (mirrors Content) ─────────────────────────────────
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String, nullable=False)  # locale-specific slug (no global uniqueness)
    meta_title = Column(Text, nullable=True)
    meta_description = Column(Text, nullable=True)
    meta_keywords = Column(Text, nullable=True)

    # ── Translation lifecycle ─────────────────────────────────────────────────
    status = Column(
        String(20),
        nullable=False,
        default=TranslationStatus.draft.value,
    )
    is_rtl = Column(Boolean, nullable=False, default=False)

    # ── Audit / workflow ──────────────────────────────────────────────────────
    translated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    # String-referenced to avoid circular imports with content.py
    content = relationship("Content", back_populates="translations")
    translated_by = relationship(
        "User",
        foreign_keys=[translated_by_id],
        lazy="select",
    )
    reviewed_by = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
        lazy="select",
    )

    __table_args__ = (
        # One translation per (content, locale) pair
        UniqueConstraint("content_id", "locale", name="uq_content_translation_locale"),
        Index("idx_ct_content_locale", "content_id", "locale"),
        Index("idx_ct_locale_status", "locale", "status"),
        Index("idx_ct_slug", "locale", "slug"),
    )
