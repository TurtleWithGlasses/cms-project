"""
Media Model

Represents uploaded media files (images, documents, etc.)
"""

from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Media(Base):
    """Media file model"""

    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    mime_type = Column(String, nullable=False)
    file_type = Column(String, nullable=False, index=True)  # image, document, video, etc.

    # Image-specific fields
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    sizes = Column(JSON, default=dict, nullable=False)  # {"small": "path", "medium": "path", "large": "path"}

    # Descriptive metadata
    alt_text = Column(String, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list, nullable=False)  # ["tag1", "tag2"]

    # Organization
    folder_id = Column(Integer, ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    uploader = relationship("User", back_populates="uploaded_media")
    folder = relationship("MediaFolder", back_populates="media_items")

    # Performance indexes
    __table_args__ = (
        Index("ix_media_uploaded_by", "uploaded_by"),
        Index("ix_media_uploaded_at", "uploaded_at"),
        Index("ix_media_folder_id", "folder_id"),
    )

    def __repr__(self):
        return f"<Media(id={self.id}, filename={self.filename}, type={self.file_type})>"
