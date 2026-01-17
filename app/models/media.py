"""
Media Model

Represents uploaded media files (images, documents, etc.)
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, String
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

    # Metadata
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    uploader = relationship("User", back_populates="uploaded_media")

    # Performance indexes
    __table_args__ = (
        Index("ix_media_uploaded_by", "uploaded_by"),
        Index("ix_media_uploaded_at", "uploaded_at"),
    )

    def __repr__(self):
        return f"<Media(id={self.id}, filename={self.filename}, type={self.file_type})>"
