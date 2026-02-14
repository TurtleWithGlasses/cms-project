"""
Comment Model

Supports threaded comments with nested replies, moderation status,
and user attribution.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

from app.database import Base


class CommentStatus(str, enum.Enum):
    """Comment moderation status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SPAM = "spam"


class Comment(Base):
    """
    Comment model for content engagement.

    Supports:
    - Nested replies via parent_id (self-referential)
    - Moderation workflow
    - Soft delete capability
    - User attribution
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Content relationship
    content_id = Column(Integer, ForeignKey("content.id", ondelete="CASCADE"), nullable=False, index=True)

    # Author relationship
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Parent comment for nested replies (null = top-level comment)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True)

    # Comment body
    body = Column(Text, nullable=False)

    # Moderation status
    status = Column(Enum(CommentStatus), default=CommentStatus.PENDING, nullable=False, index=True)

    # Soft delete flag
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Edit tracking
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime, nullable=True)

    # Relationships
    content = relationship("Content", back_populates="comments")
    user = relationship("User", back_populates="comments")

    # Self-referential relationship for nested replies
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship(
        "Comment",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Engagement relationships
    reactions = relationship("CommentReaction", back_populates="comment", cascade="all, delete-orphan", lazy="selectin")
    reports = relationship("CommentReport", back_populates="comment", cascade="all, delete-orphan", lazy="noload")
    edit_history = relationship(
        "CommentEditHistory", back_populates="comment", cascade="all, delete-orphan", lazy="noload"
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_comments_content_status", "content_id", "status"),
        Index("ix_comments_user_created", "user_id", "created_at"),
        Index("ix_comments_parent_created", "parent_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, content_id={self.content_id}, user_id={self.user_id})>"
