"""User session tracking for security and session management."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class UserSession(Base):
    """Track active user sessions for security and management."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session identification
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)

    # Device and location info
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    device_name = Column(String(255), nullable=True)  # Chrome on Windows, Safari on iPhone
    browser = Column(String(100), nullable=True)
    browser_version = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    location = Column(String(255), nullable=True)  # City, Country

    # User agent string for detailed analysis
    user_agent = Column(Text, nullable=True)

    # Session status
    is_active = Column(Boolean, default=True, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)  # Current session marker

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", backref="sessions")


class LoginAttempt(Base):
    """Track login attempts for security monitoring."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Attempt details
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Result
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)  # invalid_password, account_locked, etc.

    # Timestamps
    attempted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="login_attempts")
