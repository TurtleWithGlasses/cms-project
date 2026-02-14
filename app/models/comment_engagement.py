"""
Comment Engagement Models

Supports comment reactions (like/dislike), reporting/flagging,
and edit history tracking.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ReactionType(str, enum.Enum):
    """Reaction types for comments."""

    LIKE = "like"
    DISLIKE = "dislike"


class ReportReason(str, enum.Enum):
    """Reasons for reporting a comment."""

    SPAM = "spam"
    HARASSMENT = "harassment"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    """Status of a comment report."""

    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


class CommentReaction(Base):
    """
    Reaction on a comment (like or dislike).

    Each user can have at most one reaction per comment.
    """

    __tablename__ = "comment_reactions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reaction_type = Column(Enum(ReactionType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    comment = relationship("Comment", back_populates="reactions")
    user = relationship("User")

    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_reaction_user"),)

    def __repr__(self) -> str:
        return f"<CommentReaction(id={self.id}, comment={self.comment_id}, user={self.user_id}, type={self.reaction_type})>"


class CommentReport(Base):
    """
    Report/flag on a comment for moderation review.

    Each user can report a comment at most once.
    """

    __tablename__ = "comment_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(Enum(ReportReason), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    comment = relationship("Comment", back_populates="reports")
    reporter = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_comment_report_user"),)

    def __repr__(self) -> str:
        return f"<CommentReport(id={self.id}, comment={self.comment_id}, reason={self.reason})>"


class CommentEditHistory(Base):
    """
    Tracks previous versions of a comment body when edited.
    """

    __tablename__ = "comment_edit_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_body = Column(Text, nullable=False)
    edited_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    edited_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    comment = relationship("Comment", back_populates="edit_history")
    editor = relationship("User")

    def __repr__(self) -> str:
        return f"<CommentEditHistory(id={self.id}, comment={self.comment_id})>"
