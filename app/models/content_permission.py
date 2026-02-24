"""
ContentPermission Model — Phase 6.5

Object-level (per-content-item) permission grant/deny.

A row represents: "for content_id X, user Y (or role Z) has permission P
granted (True) or denied (False)".

Grant/deny semantics at query time (PermissionService):
  - Explicit deny (granted=False) overrides global role grant.
  - Explicit grant (granted=True) overrides global role deny.
  - If no object-level row exists, fall back to global role permissions.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class ContentPermission(Base):
    """Object-level permission override for a specific content item."""

    __tablename__ = "content_permissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Target content item
    content_id = Column(
        Integer,
        ForeignKey("content.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Subject: either a specific user OR a role name (mutually exclusive)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role_name = Column(String(50), nullable=True)  # e.g. "editor", "manager"

    # The permission token being overridden, e.g. "content.update"
    permission = Column(String(100), nullable=False)

    # True = grant, False = explicit deny
    granted = Column(Boolean, nullable=False, default=True)

    # Audit fields
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    content = relationship("Content", backref="object_permissions")
    user = relationship("User", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Compound indexes for efficient lookup
    __table_args__ = (
        Index("ix_content_perm_content_user", "content_id", "user_id"),
        Index("ix_content_perm_content_role", "content_id", "role_name"),
    )

    def __repr__(self) -> str:
        subject = f"user={self.user_id}" if self.user_id else f"role={self.role_name}"
        return (
            f"<ContentPermission(id={self.id}, content={self.content_id}, "
            f"{subject}, perm={self.permission!r}, granted={self.granted})>"
        )
