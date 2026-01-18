"""
Webhook Model

Provides webhook subscription management for event-driven integrations.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class WebhookEvent(str, enum.Enum):
    """Available webhook events."""

    # Content events
    CONTENT_CREATED = "content.created"
    CONTENT_UPDATED = "content.updated"
    CONTENT_DELETED = "content.deleted"
    CONTENT_PUBLISHED = "content.published"
    CONTENT_UNPUBLISHED = "content.unpublished"

    # Comment events
    COMMENT_CREATED = "comment.created"
    COMMENT_APPROVED = "comment.approved"
    COMMENT_DELETED = "comment.deleted"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Media events
    MEDIA_UPLOADED = "media.uploaded"
    MEDIA_DELETED = "media.deleted"

    # Wildcard
    ALL = "*"


class WebhookStatus(str, enum.Enum):
    """Webhook subscription status."""

    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"  # Too many failures
    DISABLED = "disabled"


class Webhook(Base):
    """
    Webhook subscription model.

    Features:
    - Event-based subscriptions
    - Secret for signature verification
    - Retry handling with failure tracking
    - Rate limiting
    """

    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Webhook identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Target URL
    url = Column(String(2048), nullable=False)

    # Authentication secret (for HMAC signature)
    secret = Column(String(64), nullable=False)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Events (comma-separated list of WebhookEvent values)
    events = Column(Text, nullable=False)

    # Status
    status = Column(Enum(WebhookStatus), default=WebhookStatus.ACTIVE, nullable=False)

    # Failure tracking
    failure_count = Column(Integer, default=0, nullable=False)
    last_failure_at = Column(DateTime, nullable=True)
    last_failure_reason = Column(Text, nullable=True)

    # Success tracking
    last_triggered_at = Column(DateTime, nullable=True)
    total_deliveries = Column(Integer, default=0, nullable=False)
    successful_deliveries = Column(Integer, default=0, nullable=False)

    # Configuration
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Custom headers (JSON string)
    headers = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="webhooks")
    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_webhooks_user_active", "user_id", "is_active"),
        Index("ix_webhooks_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Webhook(id={self.id}, name={self.name}, url={self.url[:50]})>"

    def get_events(self) -> list[str]:
        """Get list of subscribed events."""
        if not self.events:
            return []
        return [e.strip() for e in self.events.split(",")]

    def is_subscribed_to(self, event: str) -> bool:
        """Check if webhook is subscribed to an event."""
        events = self.get_events()
        return "*" in events or event in events


class WebhookDelivery(Base):
    """
    Webhook delivery log for tracking delivery attempts.
    """

    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Webhook reference
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event info
    event = Column(String(50), nullable=False)
    payload = Column(Text, nullable=False)  # JSON payload

    # Delivery status
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False, nullable=False)

    # Error info
    error_message = Column(Text, nullable=True)

    # Timing
    duration_ms = Column(Integer, nullable=True)
    attempt = Column(Integer, default=1, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    # Indexes
    __table_args__ = (
        Index("ix_webhook_deliveries_webhook_created", "webhook_id", "created_at"),
        Index("ix_webhook_deliveries_success", "success"),
    )

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, event={self.event})>"
