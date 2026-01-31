"""
Notification Preference and Template Models

Provides user notification preferences and reusable notification templates.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationChannel(str, enum.Enum):
    """Notification delivery channels."""

    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationCategory(str, enum.Enum):
    """Notification categories."""

    CONTENT = "content"  # Content updates
    COMMENTS = "comments"  # Comment notifications
    WORKFLOW = "workflow"  # Workflow state changes
    SECURITY = "security"  # Security alerts (2FA, login)
    SYSTEM = "system"  # System notifications
    MENTIONS = "mentions"  # User mentions
    DIGEST = "digest"  # Daily/weekly digests


class DigestFrequency(str, enum.Enum):
    """Digest email frequency."""

    NEVER = "never"
    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationTemplate(Base):
    """
    Notification template model.

    Reusable templates for notifications with variable substitution.
    """

    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Template identification
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Category
    category = Column(Enum(NotificationCategory), nullable=False, index=True)

    # Template content (supports {{variable}} syntax)
    subject = Column(String(255), nullable=False)  # Email subject / notification title
    body_text = Column(Text, nullable=False)  # Plain text version
    body_html = Column(Text, nullable=True)  # HTML version (for email)

    # Push notification specific
    push_title = Column(String(100), nullable=True)
    push_body = Column(String(255), nullable=True)

    # Available variables (JSON array of variable names)
    variables = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, **kwargs):
        # Set Python-level default for is_active (Column defaults only apply at DB INSERT time)
        kwargs.setdefault("is_active", True)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<NotificationTemplate(id={self.id}, name={self.name})>"


class NotificationPreference(Base):
    """
    User notification preference model.

    Allows users to customize their notification settings.
    """

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Category being configured
    category = Column(Enum(NotificationCategory), nullable=False)

    # Channel preferences
    email_enabled = Column(Boolean, default=True, nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    push_enabled = Column(Boolean, default=False, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)

    # Digest settings
    digest_frequency = Column(Enum(DigestFrequency), default=DigestFrequency.IMMEDIATE, nullable=False)

    # Quiet hours (24-hour format, e.g., "22:00-08:00")
    quiet_hours = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="notification_preferences")

    # Indexes
    __table_args__ = (Index("ix_notification_preferences_user_category", "user_id", "category", unique=True),)

    def __init__(self, **kwargs):
        # Set Python-level defaults for boolean fields (Column defaults only apply at DB INSERT time)
        kwargs.setdefault("email_enabled", True)
        kwargs.setdefault("in_app_enabled", True)
        kwargs.setdefault("push_enabled", False)
        kwargs.setdefault("sms_enabled", False)
        kwargs.setdefault("digest_frequency", DigestFrequency.IMMEDIATE)
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<NotificationPreference(id={self.id}, user={self.user_id}, category={self.category})>"


class NotificationQueue(Base):
    """
    Notification queue model.

    Queues notifications for batch processing and digest emails.
    """

    __tablename__ = "notification_queue"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Recipient
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Template reference
    template_id = Column(
        Integer,
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Notification content
    category = Column(Enum(NotificationCategory), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    # Variables (JSON string)
    variables = Column(Text, nullable=True)

    # Delivery settings
    channel = Column(Enum(NotificationChannel), nullable=False)

    # Status
    is_sent = Column(Boolean, default=False, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)
    is_digest = Column(Boolean, default=False, nullable=False)  # Part of digest

    # Error handling
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    # Scheduling
    scheduled_for = Column(DateTime, nullable=True, index=True)  # For scheduled notifications
    sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User")
    template = relationship("NotificationTemplate")

    # Indexes
    __table_args__ = (
        Index("ix_notification_queue_pending", "is_sent", "scheduled_for"),
        Index("ix_notification_queue_user_unread", "user_id", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<NotificationQueue(id={self.id}, user={self.user_id}, sent={self.is_sent})>"


class NotificationDigest(Base):
    """
    Notification digest tracking.

    Tracks when digests were sent to users.
    """

    __tablename__ = "notification_digests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # User reference
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Digest period
    frequency = Column(Enum(DigestFrequency), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Stats
    notification_count = Column(Integer, default=0, nullable=False)

    # Status
    sent_at = Column(DateTime, nullable=True)
    is_sent = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (Index("ix_notification_digests_user_period", "user_id", "period_start"),)

    def __repr__(self) -> str:
        return f"<NotificationDigest(id={self.id}, user={self.user_id}, frequency={self.frequency})>"
