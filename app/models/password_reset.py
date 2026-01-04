"""
Password Reset Model

Stores password reset tokens with expiration.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.database import Base


class PasswordResetToken(Base):
    """Model for password reset tokens"""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="password_reset_tokens")

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not used)"""
        return not self.used and not self.is_expired()

    @staticmethod
    def get_expiry_time(hours: int = 1) -> datetime:
        """Get expiry time (default 1 hour from now)"""
        return datetime.utcnow() + timedelta(hours=hours)
