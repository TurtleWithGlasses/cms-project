"""
MediaFolder Model

Represents folders for organizing uploaded media files.
"""

import re
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


def _slugify(text: str) -> str:
    """Generate a URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


class MediaFolder(Base):
    """Media folder for organizing files"""

    __tablename__ = "media_folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    parent = relationship("MediaFolder", remote_side=[id], backref="subfolders")
    user = relationship("User", back_populates="media_folders")
    media_items = relationship("Media", back_populates="folder")

    # Performance indexes
    __table_args__ = (
        Index("ix_media_folders_user_id", "user_id"),
        Index("ix_media_folders_parent_id", "parent_id"),
    )

    def __repr__(self):
        return f"<MediaFolder(id={self.id}, name={self.name}, user_id={self.user_id})>"
