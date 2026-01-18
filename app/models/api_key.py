"""
API Key Model

Provides API key management for third-party integrations.
"""

import enum
import secrets
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class APIKeyScope(str, enum.Enum):
    """Available API key scopes/permissions."""

    READ = "read"  # Read-only access
    WRITE = "write"  # Read and write access
    ADMIN = "admin"  # Full administrative access
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    MEDIA_READ = "media:read"
    MEDIA_WRITE = "media:write"
    USERS_READ = "users:read"
    WEBHOOKS = "webhooks"


class APIKey(Base):
    """
    API Key model for authenticating third-party integrations.

    Features:
    - Secure key generation with prefix for identification
    - Scoped permissions
    - Usage tracking
    - Expiration support
    - Rate limiting per key
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Key identification
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # The actual key - prefix (visible) + secret (hashed)
    key_prefix = Column(String(8), unique=True, nullable=False, index=True)
    key_hash = Column(String(128), nullable=False)

    # Owner
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Permissions (stored as comma-separated scopes)
    scopes = Column(Text, nullable=False, default="read")

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Expiration (null = never expires)
    expires_at = Column(DateTime, nullable=True)

    # Rate limiting
    rate_limit = Column(Integer, default=1000, nullable=False)  # requests per hour
    rate_limit_remaining = Column(Integer, default=1000, nullable=False)
    rate_limit_reset = Column(DateTime, nullable=True)

    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    # Indexes
    __table_args__ = (
        Index("ix_api_keys_user_active", "user_id", "is_active"),
        Index("ix_api_keys_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            tuple: (full_key, prefix, secret)
            - full_key: The complete key to show to user (only once!)
            - prefix: The visible prefix (e.g., "cms_xxxx")
            - secret: The secret part to hash and store
        """
        prefix = "cms_" + secrets.token_hex(2)  # 8 chars total
        secret = secrets.token_urlsafe(32)  # 43 chars
        full_key = f"{prefix}_{secret}"
        return full_key, prefix, secret

    def get_scopes(self) -> list[str]:
        """Get list of scopes for this key."""
        if not self.scopes:
            return []
        return [s.strip() for s in self.scopes.split(",")]

    def has_scope(self, scope: str) -> bool:
        """Check if key has a specific scope."""
        scopes = self.get_scopes()
        # Admin scope grants all permissions
        if "admin" in scopes:
            return True
        # Write scope includes read
        if scope.endswith(":read") and scope.replace(":read", ":write") in scopes:
            return True
        return scope in scopes

    def is_expired(self) -> bool:
        """Check if the key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
