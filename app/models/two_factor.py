"""
Two-Factor Authentication Model

Stores TOTP secrets and backup codes for users who enable 2FA.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class TwoFactorAuth(Base):
    """
    Two-factor authentication settings for a user.

    Stores:
    - TOTP secret (encrypted)
    - Backup codes (hashed)
    - Verification status
    """

    __tablename__ = "two_factor_auth"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # User relationship (one-to-one)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # TOTP secret (should be encrypted in production)
    secret = Column(String(64), nullable=False)

    # Whether 2FA is fully enabled (after initial verification)
    is_enabled = Column(Boolean, default=False, nullable=False)

    # Backup codes (hashed) - stored as JSON array
    backup_codes = Column(Text, nullable=True)  # JSON string of hashed backup codes

    # Recovery email (optional secondary verification)
    recovery_email = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    enabled_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)

    # Relationship
    user = relationship("User", back_populates="two_factor_auth")

    def __repr__(self) -> str:
        return f"<TwoFactorAuth(user_id={self.user_id}, enabled={self.is_enabled})>"
